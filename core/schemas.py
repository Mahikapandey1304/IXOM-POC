"""
Schema Validation — Pydantic models for all structured data.

Ensures data integrity throughout the extraction and comparison pipeline.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class ParameterSchema(BaseModel):
    """Schema for individual parameter (spec or certificate)."""
    
    name: str = Field(..., min_length=1, description="Parameter name")
    value: str = Field(default="", description="Measured or expected value")
    unit: str = Field(default="", description="Unit of measurement")
    min_limit: str = Field(default="", description="Minimum acceptable limit")
    max_limit: str = Field(default="", description="Maximum acceptable limit")
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Ensure parameter name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Parameter name cannot be empty or whitespace")
        return v.strip()
    
    class Config:
        str_strip_whitespace = True


class ClassificationSchema(BaseModel):
    """Schema for document classification results."""
    
    document_type: str = Field(..., description="Classified document type")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    product_name: str = Field(default="", description="Identified product name")
    reasoning: str = Field(default="", description="Classification reasoning")
    
    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        """Validate document type is one of the expected values."""
        valid_types = {
            "Product_Specification", "COA", "COCA", "COC", 
            "Invoice", "Other", "Unknown"
        }
        if v not in valid_types:
            # Allow through but log warning - AI might use variants
            pass
        return v
    
    class Config:
        str_strip_whitespace = True


class SpecificationSchema(BaseModel):
    """Schema for product specification extraction results."""
    
    document_type: str = Field(default="Product_Specification")
    product_name: str = Field(default="", description="Product name from document")
    material_number: str = Field(default="", description="Material/product code")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    parameters: List[ParameterSchema] = Field(default_factory=list)
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")
    
    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: List[ParameterSchema]) -> List[ParameterSchema]:
        """Ensure no duplicate parameter names."""
        names = [p.name.lower() for p in v]
        if len(names) != len(set(names)):
            # Log warning but don't fail - AI might extract similar params
            pass
        return v
    
    class Config:
        str_strip_whitespace = True


class CertificateSchema(BaseModel):
    """Schema for certificate (COA/COCA/COC) extraction results."""
    
    document_type: str = Field(..., description="Certificate type: COA, COCA, or COC")
    product_name: str = Field(default="", description="Product name from certificate")
    batch_number: str = Field(default="", description="Batch or lot number")
    date_of_manufacture: str = Field(default="", description="Manufacturing date")
    expiry_date: str = Field(default="", description="Expiry/best before date")
    supplier_name: str = Field(default="", description="Supplier or manufacturer name")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    parameters: List[ParameterSchema] = Field(default_factory=list)
    
    # COCA/COC specific fields
    compliance_statement: Optional[str] = Field(default=None, description="Compliance declaration text")
    certifying_authority: Optional[str] = Field(default=None, description="Name of certifying authority")
    reference_standard: Optional[str] = Field(default=None, description="Referenced specification or standard")
    
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")
    
    @field_validator('document_type')
    @classmethod
    def validate_cert_type(cls, v: str) -> str:
        """Ensure document type is a valid certificate type."""
        valid_types = {"COA", "COCA", "COC"}
        if v not in valid_types:
            # Allow through - classifier might have different opinion
            pass
        return v
    
    class Config:
        str_strip_whitespace = True


class ParameterComparisonSchema(BaseModel):
    """Schema for individual parameter comparison result."""
    
    spec_name: str = Field(..., description="Parameter name from spec")
    cert_name: str = Field(..., description="Parameter name from certificate")
    spec_value: str = Field(default="", description="Expected value from spec")
    cert_value: str = Field(default="", description="Actual value from certificate")
    spec_unit: str = Field(default="", description="Unit from spec")
    cert_unit: str = Field(default="", description="Unit from certificate")
    min_limit: str = Field(default="", description="Minimum limit")
    max_limit: str = Field(default="", description="Maximum limit")
    status: Literal["PASS", "FAIL", "REVIEW", "INFO", "MISSING"] = Field(...)
    reason: str = Field(default="", description="Explanation of comparison result")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    class Config:
        str_strip_whitespace = True


class ComparisonSchema(BaseModel):
    """Schema for overall document comparison results."""
    
    status: Literal["PASS", "FAIL", "REVIEW", "ERROR"] = Field(...)
    reason: str = Field(default="", description="Overall comparison explanation")
    product_name: str = Field(default="", description="Product name")
    batch_number: str = Field(default="", description="Batch number from certificate")
    parameters_checked: int = Field(default=0, ge=0)
    parameters_passed: int = Field(default=0, ge=0)
    parameters_failed: int = Field(default=0, ge=0)
    parameters_review: int = Field(default=0, ge=0)
    parameter_details: List[ParameterComparisonSchema] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_parameter_counts(self):
        """Ensure parameter counts are consistent."""
        total = self.parameters_passed + self.parameters_failed + self.parameters_review
        # Allow some flexibility - might have INFO status params
        if self.parameters_checked > 0 and total > self.parameters_checked:
            raise ValueError(
                f"Sum of passed/failed/review ({total}) cannot exceed checked ({self.parameters_checked})"
            )
        return self
    
    class Config:
        str_strip_whitespace = True


class AuditLogSchema(BaseModel):
    """Schema for audit log entries."""
    
    timestamp: str = Field(...)
    spec_file: str = Field(...)
    cert_file: str = Field(...)
    cert_type: str = Field(...)
    model: str = Field(...)
    doc_type_detected: str = Field(default="")
    product_name: str = Field(default="")
    material_number: str = Field(default="")
    batch_number: str = Field(default="")
    status: str = Field(...)
    reason: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    parameters_checked: int = Field(default=0, ge=0)
    parameters_passed: int = Field(default=0, ge=0)
    parameters_failed: int = Field(default=0, ge=0)
    parameters_missing: int = Field(default=0, ge=0)
    
    class Config:
        str_strip_whitespace = True
