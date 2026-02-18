"""
Tests for Pydantic schema validation.

Tests ensure all schemas correctly validate valid data and reject invalid data.
"""

import pytest
from pydantic import ValidationError

from core.schemas import (
    ParameterSchema,
    ClassificationSchema,
    SpecificationSchema,
    CertificateSchema,
    ParameterComparisonSchema,
    ComparisonSchema,
)


# ─── ParameterSchema Tests ────────────────────────────────────────────

def test_parameter_schema_valid():
    """Test valid parameter creation."""
    param = ParameterSchema(
        name="pH",
        value="7.5",
        unit="",
        min_limit="7.0",
        max_limit="8.0"
    )
    assert param.name == "pH"
    assert param.value == "7.5"


def test_parameter_schema_strips_whitespace():
    """Test that parameter names are stripped."""
    param = ParameterSchema(name="  pH  ")
    assert param.name == "pH"


def test_parameter_schema_empty_name_fails():
    """Test that empty parameter name fails validation."""
    with pytest.raises(ValidationError):
        ParameterSchema(name="")


def test_parameter_schema_whitespace_name_fails():
    """Test that whitespace-only parameter name fails validation."""
    with pytest.raises(ValidationError):
        ParameterSchema(name="   ")


# ─── ClassificationSchema Tests ───────────────────────────────────────

def test_classification_schema_valid():
    """Test valid classification."""
    classification = ClassificationSchema(
        document_type="COA",
        confidence_score=0.95,
        product_name="Test Product",
        reasoning="Clear COA format"
    )
    assert classification.document_type == "COA"
    assert classification.confidence_score == 0.95


def test_classification_schema_confidence_bounds():
    """Test that confidence score must be between 0 and 1."""
    with pytest.raises(ValidationError):
        ClassificationSchema(
            document_type="COA",
            confidence_score=1.5
        )
    
    with pytest.raises(ValidationError):
        ClassificationSchema(
            document_type="COA",
            confidence_score=-0.1
        )


def test_classification_schema_defaults():
    """Test default values for optional fields."""
    classification = ClassificationSchema(
        document_type="COA",
        confidence_score=0.9
    )
    assert classification.product_name == ""
    assert classification.reasoning == ""


# ─── SpecificationSchema Tests ────────────────────────────────────────

def test_specification_schema_valid():
    """Test valid specification."""
    spec = SpecificationSchema(
        product_name="Sodium Chlorite 31%",
        material_number="NACLO2-31",
        confidence_score=0.95,
        parameters=[
            ParameterSchema(name="pH", min_limit="12.5", max_limit="13.5")
        ]
    )
    assert spec.product_name == "Sodium Chlorite 31%"
    assert len(spec.parameters) == 1


def test_specification_schema_empty_parameters():
    """Test specification with no parameters."""
    spec = SpecificationSchema(
        product_name="Test Product",
        parameters=[]
    )
    assert len(spec.parameters) == 0


def test_specification_schema_defaults():
    """Test default values."""
    spec = SpecificationSchema()
    assert spec.document_type == "Product_Specification"
    assert spec.product_name == ""
    assert spec.confidence_score == 0.0
    assert spec.parameters == []


# ─── CertificateSchema Tests ──────────────────────────────────────────

def test_certificate_schema_coa():
    """Test valid COA certificate."""
    cert = CertificateSchema(
        document_type="COA",
        product_name="Test Product",
        batch_number="B12345",
        confidence_score=0.9,
        parameters=[
            ParameterSchema(name="pH", value="7.5")
        ]
    )
    assert cert.document_type == "COA"
    assert cert.batch_number == "B12345"


def test_certificate_schema_coca_with_compliance():
    """Test COCA certificate with compliance statement."""
    cert = CertificateSchema(
        document_type="COCA",
        product_name="Test Product",
        compliance_statement="Product meets all specifications",
        certifying_authority="Quality Dept",
        reference_standard="ISO 9001"
    )
    assert cert.document_type == "COCA"
    assert cert.compliance_statement == "Product meets all specifications"


def test_certificate_schema_defaults():
    """Test default values."""
    cert = CertificateSchema(document_type="COA")
    assert cert.product_name == ""
    assert cert.batch_number == ""
    assert cert.parameters == []


# ─── ComparisonSchema Tests ───────────────────────────────────────────

def test_comparison_schema_valid():
    """Test valid comparison result."""
    comparison = ComparisonSchema(
        status="PASS",
        reason="All parameters within limits",
        product_name="Test Product",
        batch_number="B12345",
        parameters_checked=5,
        parameters_passed=5,
        parameters_failed=0,
        parameters_review=0
    )
    assert comparison.status == "PASS"
    assert comparison.parameters_checked == 5


def test_comparison_schema_status_values():
    """Test that status must be one of allowed values."""
    # These should work
    for status in ["PASS", "FAIL", "REVIEW", "ERROR"]:
        comparison = ComparisonSchema(status=status)
        assert comparison.status == status


def test_comparison_schema_parameter_counts():
    """Test parameter count validation."""
    # Valid: sum of passed/failed/review <= checked
    comparison = ComparisonSchema(
        status="PASS",
        parameters_checked=10,
        parameters_passed=8,
        parameters_failed=1,
        parameters_review=1
    )
    assert comparison.parameters_checked == 10
    
    # Invalid: sum > checked
    with pytest.raises(ValidationError):
        ComparisonSchema(
            status="PASS",
            parameters_checked=5,
            parameters_passed=4,
            parameters_failed=2,
            parameters_review=1
        )


def test_comparison_schema_defaults():
    """Test default values."""
    comparison = ComparisonSchema(status="PASS")
    assert comparison.reason == ""
    assert comparison.parameters_checked == 0
    assert comparison.parameter_details == []


# ─── ParameterComparisonSchema Tests ──────────────────────────────────

def test_parameter_comparison_schema_valid():
    """Test valid parameter comparison."""
    param_comp = ParameterComparisonSchema(
        spec_name="pH",
        cert_name="pH",
        spec_value="7.0-8.0",
        cert_value="7.5",
        status="PASS",
        reason="Within specification",
        confidence=1.0
    )
    assert param_comp.status == "PASS"
    assert param_comp.confidence == 1.0


def test_parameter_comparison_schema_status_values():
    """Test that status must be one of allowed values."""
    for status in ["PASS", "FAIL", "REVIEW", "INFO", "MISSING"]:
        param_comp = ParameterComparisonSchema(
            spec_name="test",
            cert_name="test",
            status=status
        )
        assert param_comp.status == status


# ─── Integration Tests ────────────────────────────────────────────────

def test_specification_with_nested_parameters():
    """Test specification with multiple nested parameters."""
    spec = SpecificationSchema(
        product_name="Test Product",
        parameters=[
            ParameterSchema(name="pH", min_limit="7.0", max_limit="8.0"),
            ParameterSchema(name="Density", value="1.05", unit="g/mL"),
            ParameterSchema(name="Appearance", value="Clear liquid")
        ]
    )
    assert len(spec.parameters) == 3
    assert spec.parameters[0].name == "pH"
    assert spec.parameters[1].unit == "g/mL"


def test_comparison_with_nested_details():
    """Test comparison with nested parameter details."""
    comparison = ComparisonSchema(
        status="REVIEW",
        parameters_checked=2,
        parameters_passed=1,
        parameters_review=1,
        parameter_details=[
            ParameterComparisonSchema(
                spec_name="pH",
                cert_name="pH",
                status="PASS"
            ),
            ParameterComparisonSchema(
                spec_name="Density",
                cert_name="Specific Gravity",
                status="REVIEW",
                reason="Name mismatch needs verification"
            )
        ]
    )
    assert len(comparison.parameter_details) == 2
    assert comparison.parameter_details[1].status == "REVIEW"
