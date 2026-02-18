"""
Retry Configuration — Reusable retry decorators for robust error handling.

Provides retry logic for OpenAI API calls, file I/O, and PDF operations.
"""

import logging
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
from openai import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)

# Configure logging for retry attempts
logger = logging.getLogger(__name__)


# ─── OpenAI API Retry Decorator ──────────────────────────────────────

retry_openai_call = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        APITimeoutError,
        APIConnectionError,
        RateLimitError,
        InternalServerError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
"""
Retry decorator for OpenAI API calls.

Retries up to 3 times with exponential backoff (1-10 seconds) on:
- API timeouts
- Connection errors
- Rate limit errors
- Internal server errors

Raises the last exception if all retries fail.
"""


# ─── File I/O Retry Decorator ────────────────────────────────────────

retry_file_io = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((
        IOError,
        OSError,
        PermissionError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
"""
Retry decorator for file I/O operations.

Retries up to 3 times with 1-second fixed wait on:
- I/O errors
- OS errors (file locked, etc.)
- Permission errors

Raises the last exception if all retries fail.
"""


# ─── PDF Operation Retry Decorator ───────────────────────────────────

retry_pdf_operation = retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((
        IOError,
        OSError,
        RuntimeError,  # pypdfium2 may raise RuntimeError for corrupt PDFs
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
"""
Retry decorator for PDF processing operations.

Retries up to 2 times with 2-second fixed wait on:
- I/O errors
- OS errors
- Runtime errors (PDF parsing failures)

Raises the last exception if all retries fail.
"""


# ─── Helper Function for Logging ──────────────────────────────────────

def log_retry_attempt(retry_state):
    """
    Log retry attempts with context.
    
    Can be used as a callback in retry decorators for custom logging.
    """
    attempt = retry_state.attempt_number
    fn_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        logger.warning(
            f"Retry attempt {attempt} for {fn_name} failed: {type(exception).__name__}: {exception}"
        )
    else:
        logger.info(f"Retry attempt {attempt} for {fn_name} succeeded")
