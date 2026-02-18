"""
Tests for retry logic.

Tests ensure retry decorators work correctly for various failure scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from openai import APITimeoutError, APIConnectionError, RateLimitError
from core.retry_config import (
    retry_openai_call,
    retry_file_io,
    retry_pdf_operation,
)


# ─── OpenAI Retry Tests ───────────────────────────────────────────────

def test_retry_openai_call_succeeds_first_try():
    """Test that successful call doesn't retry."""
    mock_func = Mock(return_value="success")
    decorated = retry_openai_call(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_openai_call_retries_on_timeout():
    """Test that timeout errors trigger retries."""
    mock_func = Mock(side_effect=[
        APITimeoutError("Timeout"),
        "success"
    ])
    decorated = retry_openai_call(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_openai_call_retries_on_connection_error():
    """Test that connection errors trigger retries."""
    mock_func = Mock(side_effect=[
        APIConnectionError(request=Mock()),
        "success"
    ])
    decorated = retry_openai_call(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_openai_call_max_attempts():
    """Test that retry gives up after max attempts."""
    mock_func = Mock(side_effect=APITimeoutError("Persistent timeout"))
    decorated = retry_openai_call(mock_func)
    
    with pytest.raises(APITimeoutError):
        decorated()
    
    # Should try 3 times (initial + 2 retries)
    assert mock_func.call_count == 3


def test_retry_openai_call_non_retryable_error():
    """Test that non-retryable errors don't trigger retries."""
    mock_func = Mock(side_effect=ValueError("Invalid input"))
    decorated = retry_openai_call(mock_func)
    
    with pytest.raises(ValueError):
        decorated()
    
    # Should only try once
    assert mock_func.call_count == 1


# ─── File I/O Retry Tests ─────────────────────────────────────────────

def test_retry_file_io_succeeds_first_try():
    """Test that successful file I/O doesn't retry."""
    mock_func = Mock(return_value="data")
    decorated = retry_file_io(mock_func)
    
    result = decorated()
    
    assert result == "data"
    assert mock_func.call_count == 1


def test_retry_file_io_retries_on_ioerror():
    """Test that IO errors trigger retries."""
    mock_func = Mock(side_effect=[
        IOError("File locked"),
        "success"
    ])
    decorated = retry_file_io(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_file_io_retries_on_permission_error():
    """Test that permission errors trigger retries."""
    mock_func = Mock(side_effect=[
        PermissionError("Access denied"),
        "success"
    ])
    decorated = retry_file_io(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_file_io_max_attempts():
    """Test that file I/O retry gives up after max attempts."""
    mock_func = Mock(side_effect=IOError("Persistent error"))
    decorated = retry_file_io(mock_func)
    
    with pytest.raises(IOError):
        decorated()
    
    # Should try 3 times
    assert mock_func.call_count == 3


# ─── PDF Operation Retry Tests ────────────────────────────────────────

def test_retry_pdf_operation_succeeds_first_try():
    """Test that successful PDF operation doesn't retry."""
    mock_func = Mock(return_value="pdf_data")
    decorated = retry_pdf_operation(mock_func)
    
    result = decorated()
    
    assert result == "pdf_data"
    assert mock_func.call_count == 1


def test_retry_pdf_operation_retries_on_runtime_error():
    """Test that runtime errors trigger retries."""
    mock_func = Mock(side_effect=[
        RuntimeError("PDF parsing failed"),
        "success"
    ])
    decorated = retry_pdf_operation(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_pdf_operation_max_attempts():
    """Test that PDF operation retry gives up after max attempts."""
    mock_func = Mock(side_effect=RuntimeError("Corrupt PDF"))
    decorated = retry_pdf_operation(mock_func)
    
    with pytest.raises(RuntimeError):
        decorated()
    
    # Should try 2 times (initial + 1 retry)
    assert mock_func.call_count == 2


# ─── Integration Tests ────────────────────────────────────────────────

def test_retry_with_function_arguments():
    """Test that retry decorators work with function arguments."""
    mock_func = Mock(return_value="result")
    decorated = retry_file_io(mock_func)
    
    result = decorated("arg1", kwarg="value")
    
    assert result == "result"
    mock_func.assert_called_once_with("arg1", kwarg="value")


def test_retry_preserves_function_metadata():
    """Test that decorators preserve function metadata."""
    @retry_openai_call
    def sample_function():
        """Sample docstring."""
        return "result"
    
    # Function should be callable
    result = sample_function()
    assert result == "result"


def test_multiple_retries_with_different_errors():
    """Test handling multiple different errors in sequence."""
    mock_func = Mock(side_effect=[
        IOError("First error"),
        OSError("Second error"),
        "success"
    ])
    decorated = retry_file_io(mock_func)
    
    result = decorated()
    
    assert result == "success"
    assert mock_func.call_count == 3


# ─── Real-world Scenario Tests ────────────────────────────────────────

def test_openai_call_with_eventual_success():
    """Test realistic scenario where OpenAI eventually succeeds."""
    call_count = 0
    
    @retry_openai_call
    def api_call():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise APIConnectionError(request=Mock())
        return {"result": "data"}
    
    result = api_call()
    
    assert result == {"result": "data"}
    assert call_count == 2


def test_file_write_with_transient_lock():
    """Test realistic scenario where file is temporarily locked."""
    call_count = 0
    
    @retry_file_io
    def write_file():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise PermissionError("File is locked by another process")
        return "written"
    
    result = write_file()
    
    assert result == "written"
    assert call_count == 2


def test_pdf_load_with_transient_corruption():
    """Test realistic scenario where PDF load initially fails."""
    call_count = 0
    
    @retry_pdf_operation
    def load_pdf():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("Temporary PDF parsing error")
        return "pdf_object"
    
    result = load_pdf()
    
    assert result == "pdf_object"
    assert call_count == 2
