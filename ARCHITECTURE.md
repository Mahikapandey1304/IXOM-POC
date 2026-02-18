# Intelligent Safety Net -- Architecture and Technical Documentation

## Document Information

| Field            | Value                                               |
|------------------|-----------------------------------------------------|
| Project          | Intelligent Safety Net                              |
| Organization     | IXOM                                                |
| Phase            | Phase 0 -- Proof of Concept                         |
| Version          | 1.0                                                 |
| Last Updated     | February 2026                                       |

---

## 1. Executive Summary

The Intelligent Safety Net is a standalone validation engine designed for IXOM's product safety verification workflow. It automates the comparison of supplier certificates (Certificates of Analysis, Compliance, and Conformance) against internal IXOM product specifications. The system uses OpenAI GPT-4o Vision to read PDF documents, extract structured chemical parameters, align differently-named parameters using domain knowledge, and validate compliance against specification limits.

The engine replaces a manual, error-prone process where quality assurance analysts spend 10 to 30 minutes per certificate-specification pair, visually scanning for parameter matches and performing mental arithmetic to verify limit compliance. The system processes a single pair in 30 to 60 seconds and produces an auditable, parameter-level verdict.

---

## 2. Problem Statement

### 2.1 Current Manual Process

IXOM receives supplier certificates for every batch of raw material or finished product across three industries: Food and Beverage, Health and Personal Care, and Water Treatment. Each certificate must be compared against IXOM's internal product specification to verify that all test results fall within acceptable limits.

The manual process has the following limitations:

1. Parameter names differ between specifications and certificates. A specification may list "Strength (as Acetic Acid)" while the supplier certificate shows "Acid Strength (%w/w Acetic)" for the same property. Analysts must use chemical domain knowledge to identify these as equivalent.

2. Units vary between documents. Specifications may use "mg/kg" while certificates use "ppm" for the same measurement. Analysts must perform mental conversions.

3. Measurement conditions differ. Specific gravity may be specified at "20/4" (20 degrees Celsius referenced to water at 4 degrees Celsius) but the certificate reports it at "20 degrees Celsius" -- these are the same measurement but appear different on paper.

4. Certificate types vary. Some certificates contain lab test results (COA), others contain compliance attestations with or without test data (COCA), and others are simple conformance statements (COC). Each requires a different validation approach.

5. The process does not scale. With 15 products, 3 industries, and multiple certificate types, the permutation matrix is large and growing.

### 2.2 Automation Challenges

Simple string matching fails because parameter names across documents use different terminology for the same chemical property. Rule-based systems require maintaining exhaustive lookup tables of every possible name variation for every parameter, which is impractical across suppliers, products, and industries.

The solution requires a system that understands chemical nomenclature and can intelligently align parameters that a human chemist would recognize as equivalent, even when the names share no common words.

---

## 3. System Architecture

### 3.1 High-Level Architecture

The system follows a five-stage sequential pipeline architecture. Each PDF document pair (specification and certificate) passes through all five stages in order. The stages are decoupled through well-defined JSON interfaces, allowing each stage to be tested, debugged, and improved independently.

```
+-------------------------------------------------------------------+
|                                                                   |
|   PDF FILE (Specification or Certificate)                         |
|       |                                                           |
|       v                                                           |
|   +---------------------+                                        |
|   | STAGE 1: RENDERING  |   pypdfium2 + Pillow                   |
|   | PDF --> PNG Images   |   200 DPI, max 2048x2048              |
|   +---------------------+                                        |
|       |                                                           |
|       | base64-encoded PNG images (one per page)                  |
|       v                                                           |
|   +---------------------+                                        |
|   | STAGE 2: CLASSIFY   |   GPT-4o Vision (first page only)      |
|   | Determine doc type  |   Returns: type + confidence score     |
|   +---------------------+                                        |
|       |                                                           |
|       | document_type: COA | COCA | COC | Spec | Other           |
|       v                                                           |
|   +---------------------+                                        |
|   | STAGE 3: EXTRACT    |   GPT-4o Vision (all pages)            |
|   | Parameters + values |   Spec-specific or cert-specific prompt|
|   +---------------------+                                        |
|       |                                                           |
|       | Structured JSON: product, params, limits, values          |
|       v                                                           |
|   +---------------------+                                        |
|   | STAGE 4: COMPARE    |   Three-layer comparison engine        |
|   | Align + validate    |   Token check + AI alignment + logic   |
|   +---------------------+                                        |
|       |                                                           |
|       | Per-parameter verdicts + overall status                   |
|       v                                                           |
|   +---------------------+                                        |
|   | STAGE 5: LOG        |   CSV audit trail                      |
|   | Record results      |   Persistent log + per-run summary     |
|   +---------------------+                                        |
|                                                                   |
+-------------------------------------------------------------------+
```

### 3.2 Technology Stack

| Layer              | Technology        | Version   | Purpose                                        |
|--------------------|-------------------|-----------|------------------------------------------------|
| AI Model           | OpenAI GPT-4o     | Latest    | Document classification, extraction, comparison |
| PDF Rendering      | pypdfium2         | Latest    | PDF to image conversion, pure Python            |
| Image Processing   | Pillow (PIL)      | 10.0+     | Image resizing, format conversion               |
| Backend Language   | Python            | 3.10+     | Core pipeline orchestration                     |
| Frontend           | Streamlit         | 1.30+     | Interactive web dashboard                       |
| Data Handling      | pandas + openpyxl | 2.0+      | Mapping file, audit log, data frames            |
| Environment Config | python-dotenv     | 1.0+      | API key and settings management                 |
| API Client         | openai (Python)   | 1.0+      | GPT-4o API communication                        |
| **Schema Validation** | **pydantic**   | **2.0+**  | **Data structure validation and type safety**   |
| **Retry Logic**    | **tenacity**      | **8.0+**  | **Automatic retry for transient failures**      |
| **Testing**        | **pytest**        | **7.0+**  | **Unit testing and coverage reporting**         |

### 3.3 Design Principles

**AI-First Parameter Alignment.** The system delegates parameter name matching to GPT-4o rather than attempting rule-based string matching. This is a deliberate architectural choice because the number of name variations across suppliers is effectively unbounded, and maintaining lookup tables is impractical.

**Strict on Failure, Generous on Pass.** A FAIL verdict requires mathematical proof that a value is outside specification limits. A PASS verdict is granted generously for qualitative matches such as "Pass", "Conforms", "Clear", and "ND" (Not Detected). Uncertainty defaults to REVIEW, never to FAIL.

**Separation of Matched and Unmatched Parameters.** Parameters that exist in the specification but have no counterpart in the certificate (such as visual inspection items) are classified as NOT_IN_CERT and do not affect the overall document verdict. This prevents manufacturing-floor inspection parameters from inflating false REVIEW counts.

**Deterministic Inference.** All LLM calls use temperature 0.0 to ensure reproducible results across runs.

**Structured Output Enforcement.** All LLM calls use JSON response format (`response_format: json_object`) to guarantee parseable output, eliminating markdown or prose in API responses.

**Production Hardening.** All critical operations are protected with schema validation and automatic retry logic:
- **Schema Validation**: All structured data (classifications, extractions, comparisons) is validated using Pydantic models to ensure data integrity and catch malformed LLM responses early
- **Retry Logic**: All OpenAI API calls, file I/O operations, and PDF processing include automatic retry with exponential backoff to handle transient failures (rate limits, network issues, file locks)
- **Graceful Degradation**: Validation failures are logged but don't crash the system; best-effort results with defaults are used when possible

---

## 4. Pipeline Stages -- Detailed Description

### 4.1 Stage 1: PDF Rendering

**Module:** `core/pdf_renderer.py`

**Purpose:** Convert PDF pages into high-resolution PNG images suitable for GPT-4o Vision API input.

**Implementation:**

The renderer uses `pypdfium2`, a Python binding for the PDFium library (Chromium's PDF engine). This was chosen over `pdf2image` + Poppler because pypdfium2 is a pure-Python wheel with no external binary dependencies, making it cross-platform without additional installation steps.

Each page is rendered at 200 DPI (configurable via `IMAGE_DPI`). The rendering scale is calculated as `dpi / 72` because pypdfium2 uses 72 DPI as its base resolution. The resulting PIL Image is then checked against `MAX_IMAGE_SIZE` (2048 x 2048 pixels). If either dimension exceeds this limit, the image is downscaled using Lanczos resampling while preserving aspect ratio.

The final image is saved to an in-memory buffer as PNG format and encoded to base64 for inclusion in API requests.

**Functions:**

| Function               | Input                      | Output               | Notes                                    |
|------------------------|----------------------------|-----------------------|------------------------------------------|
| `pdf_page_to_base64`  | PDF path, page number, DPI | base64 string         | Single page conversion                   |
| `pdf_to_base64_images`| PDF path, DPI, max pages   | List of base64 strings| All pages up to MAX_PAGES_PER_DOC        |
| `get_page_count`      | PDF path                   | Integer               | Page count without rendering             |

**Configuration:**

| Setting          | Value       | Rationale                                         |
|------------------|-------------|---------------------------------------------------|
| IMAGE_DPI        | 200         | Sufficient for GPT-4o to read table text clearly  |
| MAX_IMAGE_SIZE   | 2048 x 2048 | OpenAI Vision API optimal input size              |
| MAX_PAGES_PER_DOC| 10          | Cost control, most specs/certs are 1-3 pages      |

**Observed Performance:**

- Typical image sizes: 333 KB to 992 KB per page
- Rendering time: under 1 second per page
- All 34 PDFs in the test set render without errors

**Production Hardening:**

PDF loading operations are wrapped with `@retry_pdf_operation` decorator (see Section 5.6) to handle corrupted or temporarily locked PDF files. The decorator retries up to 2 times with a 2-second wait between attempts before raising the original exception.

---

### 4.2 Stage 2: Document Classification

**Module:** `core/document_classifier.py`

**Purpose:** Determine the type of document before extraction so that the correct extraction prompt can be selected.

**Implementation:**

Only the first page of the PDF is sent to GPT-4o Vision with a classification prompt. The model returns a JSON object containing:

- `document_type`: One of `Product_Specification`, `COA`, `COCA`, `COC`, `Invoice`, `Other`
- `confidence_score`: Float between 0.0 and 1.0
- `product_name`: Product name if identifiable
- `reasoning`: One-line explanation of the classification decision

The classifier uses the `detail: high` setting for the image, which costs more tokens but provides better accuracy for documents with fine print.

**Classification Categories:**

| Type                   | Description                                                |
|------------------------|------------------------------------------------------------|
| Product_Specification  | Internal IXOM spec listing parameters, limits, requirements|
| COA                    | Certificate of Analysis with lab test results              |
| COCA                   | Certificate of Compliance with Analysis (hybrid)           |
| COC                    | Certificate of Conformance (compliance attestation)        |
| Invoice                | Commercial invoice or purchase order                       |
| Other                  | Any unrecognized document type                             |

**Observed Accuracy:** 0.95 confidence score across all tested documents. No misclassifications observed in the test set.

**Production Hardening:**

- **Retry Logic:** OpenAI API calls are wrapped with `@retry_openai_call` decorator (see Section 5.6) to handle rate limits (429 errors), connection failures, and timeouts. Retries up to 3 times with exponential backoff (1s, 2s, 4s).
- **Schema Validation:** The classifier output is validated against `ClassificationSchema` (see Section 5.5) to ensure `confidence_score` is between 0.0 and 1.0, `document_type` is a valid enum value, and all required fields are present.

---

### 4.3 Stage 3: Parameter Extraction

**Modules:** `core/spec_extractor.py` and `core/cert_extractor.py`

**Purpose:** Convert unstructured PDF content into structured JSON with all parameters, values, limits, and units.

#### 4.3.1 Specification Extractor

All pages of the specification PDF are sent to GPT-4o Vision with a domain-specific prompt. The prompt includes rules for:

- Multi-grade specifications: Extract only the primary grade (the one matching the document title or listed first). Do not duplicate parameters from alternate grade tables.
- Limit notation: Single limits (max or min only), ranges (min to max), and qualitative requirements.
- Parameter categories: Chemical assay, pH, specific gravity, heavy metals, impurities, appearance, foreign matter.

**Output Schema:**

```
{
  "document_type": "Product_Specification",
  "product_name": "Acetic Acid 20% - Premium Grade",
  "material_number": "ACEACI20FG-1000L",
  "confidence_score": 0.95,
  "parameters": [
    {
      "name": "Strength (as Acetic Acid)",
      "value": "",
      "unit": "% w/w",
      "min_limit": "19.5",
      "max_limit": "20.5"
    },
    {
      "name": "Appearance and Odour",
      "value": "Clear colourless liquid with pungent odour",
      "unit": "",
      "min_limit": "",
      "max_limit": ""
    }
  ]
}
```

Numeric parameters have `min_limit` and/or `max_limit` populated with the value field empty. Qualitative parameters have `value` populated with the limits empty.

**Production Hardening (Specification Extractor):**

- **Retry Logic:** OpenAI API calls wrapped with `@retry_openai_call`, JSON file saves wrapped with `@retry_file_io` (see Section 5.6)
- **Schema Validation:** Output validated against `SpecificationSchema` (see Section 5.5) to ensure parameter count matches list length, confidence score is bounded, and all required fields are populated

#### 4.3.2 Certificate Extractor

The certificate extractor uses two distinct prompts depending on the certificate type:

**COA Prompt:** Focused on extracting lab test results. Emphasizes standardized parameter naming (use "Strength" not "Acid Strength %w/w Acetic"), extracting all numeric values with units, and capturing batch/lot numbers, dates, and supplier information.

**COCA/COC Prompt:** Handles documents that contain both compliance statements and test data. Instructs the model to extract the full compliance declaration text AND all parameters with values, not just one or the other.

**Output Schema (Certificate):**

```
{
  "document_type": "COA",
  "product_name": "ACETIC ACID 20% FLV10594 PREMIUM GRD 15L",
  "batch_number": "118541",
  "date_of_manufacture": "2024-10-15",
  "expiry_date": "",
  "supplier_name": "Supplier Name",
  "compliance_statement": "",
  "confidence_score": 0.95,
  "parameters": [
    {
      "name": "Strength (Acetic Acid)",
      "value": "20.0",
      "unit": "%w/w",
      "min_limit": "",
      "max_limit": ""
    }
  ]
}
```

**Production Hardening (Certificate Extractor):**

- **Retry Logic:** OpenAI API calls wrapped with `@retry_openai_call`, JSON file saves wrapped with `@retry_file_io` (see Section 5.6)
- **Schema Validation:** Output validated against `CertificateSchema` (see Section 5.5) to ensure parameter count matches list length, confidence score is bounded, and all required fields are populated

---

### 4.4 Stage 4: Comparison Engine

**Module:** `core/comparator.py`

**Purpose:** Compare extracted specification data against certificate data and produce a per-parameter and overall compliance verdict.

This is the most architecturally complex component. It operates in three layers:

#### Layer 1: Product Mismatch Pre-Check (Local, Zero API Cost)

Before sending data to GPT-4o for comparison, the system performs a fast local check to determine if the specification and certificate are for the same product. This catches obvious mismatches (such as an Acetic Acid specification paired with a Zinc Gluconate certificate) without consuming API tokens.

The pre-check works as follows:

1. **Tokenization:** Both product names are tokenized into lowercase words and numbers. Noise words (product, specification, grade, premium, drums, kg, etc.) are removed.

2. **Alias Expansion:** Each token is expanded using a chemical abbreviation dictionary:

   | Abbreviation | Canonical Form   |
   |-------------|------------------|
   | alum        | aluminium        |
   | aluminum    | aluminium        |
   | hypo        | hypochlorite     |
   | caustic     | hydroxide        |
   | soda        | sodium           |
   | hcl         | hydrochloric     |
   | naoh        | hydroxide        |
   | aqueous     | aqua             |
   | sulphate    | sulfate          |
   | sulphuric   | sulfuric         |
   | ferric      | iron             |
   | pac         | aluminium        |
   | naclo       | hypochlorite     |

3. **Overlap Checks:** Four checks are performed in order:
   - Direct token overlap (including expanded aliases)
   - Substring matching (checks if one token is a prefix of another, minimum 3 characters)
   - Concentration number overlap combined with minimum token overlap ratio
   - Expanded word overlap using the full alias dictionary

4. **Decision:** If all four checks find zero overlap, the system declares a product mismatch and returns FAIL immediately without calling the AI comparison. If any check finds overlap, the pair is passed to Layer 2. If uncertain, the system defaults to match and delegates to AI.

**Verified Accuracy:** 11 out of 11 test cases pass. All 7 valid product pairs are correctly matched. All 4 invalid cross-product pairs are correctly rejected.

#### Layer 2: AI-Powered Parameter Alignment and Value Comparison

The specification and certificate JSON data are sent to GPT-4o with a detailed comparison prompt. The prompt provides:

- Product matching guidance with real-world examples from the IXOM inventory
- Parameter name alignment examples showing known equivalences across supplier documents
- Specific gravity temperature notation rules (SG 20/4 equals SG at 20 degrees Celsius)
- Unit equivalence rules (percent w/w equals percent equals weight percent; mg/kg equals ppm)
- Status assignment rules with strict criteria for each verdict

The AI returns a JSON response containing:

- `product_match`: Boolean indicating whether products are the same
- `product_match_reason`: Explanation of the product match decision
- `compliance_statement_present`: Boolean for COCA/COC documents
- `compliance_statement`: Full text of any compliance declaration
- `parameters`: Array of per-parameter comparison results

Each parameter result includes:

| Field           | Description                                   |
|-----------------|-----------------------------------------------|
| spec_parameter  | Parameter name from the specification         |
| cert_parameter  | Matched parameter name from the certificate   |
| spec_min        | Minimum limit from specification              |
| spec_max        | Maximum limit from specification              |
| spec_value      | Expected qualitative value from specification |
| spec_unit       | Unit from specification                       |
| cert_value      | Actual measured value from certificate        |
| cert_unit       | Unit from certificate                         |
| status          | PASS, FAIL, REVIEW, or NOT_IN_CERT            |
| reason          | Brief explanation of the verdict              |

**Certificate Type-Specific Instructions:**

The AI prompt includes additional instructions tailored to each certificate type:

- **COA:** Compare each specification parameter against the actual measured value in the certificate.
- **COCA:** Extract and compare both the compliance statement and any test data present. Not all COCA documents have test data; some have only a compliance declaration.
- **COC:** Handle specification ranges shown in the certificate. If a range is shown instead of a single value, compare the range against specification limits (range within spec equals PASS, range overlapping but extending beyond equals REVIEW, range fully outside equals FAIL).

#### Layer 3: Status Logic Engine

After receiving the AI comparison results, the status logic engine determines the overall document verdict.

The engine separates parameters into two groups:

- **Matched parameters:** Those with status PASS, FAIL, or REVIEW (the certificate contained a corresponding value)
- **Unmatched parameters:** Those with status NOT_IN_CERT (no corresponding value in the certificate)

The overall status is determined solely by matched parameters:

```
If any matched parameter is FAIL       --> Overall FAIL
Else if any matched parameter is REVIEW --> Overall REVIEW
Else if all matched parameters are PASS --> Overall PASS
Else if only NOT_IN_CERT exists         --> Overall REVIEW
```

This separation is critical. Without it, specification parameters that describe manufacturing-floor checks (such as "Foreign Matter -- airborne unavoidable matter" or "Foreign Matter -- food safety risk") would appear in every comparison as REVIEW because they are never reported in laboratory certificates. The NOT_IN_CERT status prevents these parameters from inflating the false REVIEW count.

#### Fallback: Legacy Name-Based Matching

If the AI comparison call fails (API error, timeout, rate limit), the system falls back to a legacy name-based matching algorithm. This algorithm:

1. Builds a lookup table of certificate parameters indexed by name and normalized name
2. Attempts exact name match, then normalized name match for each specification parameter
3. Performs numeric comparison for matched parameters using the unit normalizer

This fallback produces lower accuracy (because it cannot handle name differences) but ensures the pipeline never completely fails due to a transient API issue.

**Production Hardening:**

- **Retry Logic:** OpenAI API comparison calls wrapped with `@retry_openai_call` decorator (see Section 5.6)
- **Schema Validation:** Comparison results validated against `ComparisonSchema` and `ParameterComparisonSchema` (see Section 5.5) to ensure status enums are valid, counts are consistent, and required fields are present

---

### 4.5 Stage 5: Audit Logging

**Module:** `core/logger.py`

**Purpose:** Maintain a persistent, append-only audit trail of all validation results.

**Audit Log Format (CSV):**

| Column              | Type     | Description                          |
|---------------------|----------|--------------------------------------|
| Timestamp           | ISO 8601 | When the comparison was performed    |
| Spec_File           | String   | Specification PDF filename           |
| Cert_File           | String   | Certificate PDF filename             |
| Cert_Type           | String   | COA, COCA, or COC                    |
| Model               | String   | LLM model used                       |
| Doc_Type_Detected   | String   | Classifier output                    |
| Product_Name        | String   | Product name from comparison         |
| Material_Number     | String   | IXOM material code                   |
| Batch_Number        | String   | Batch/lot number from certificate    |
| Status              | String   | PASS, FAIL, REVIEW, or ERROR         |
| Reason              | String   | Explanation (truncated to 500 chars) |
| Confidence          | Float    | Classification confidence score      |
| Parameters_Checked  | Integer  | Total parameters compared            |
| Parameters_Passed   | Integer  | Count of PASS parameters             |
| Parameters_Failed   | Integer  | Count of FAIL parameters             |
| Parameters_Missing  | Integer  | Count of REVIEW parameters           |

The audit log is append-only. Each run also generates a per-run summary CSV file containing aggregate counts and pass rate.

**Production Hardening:**

All CSV file operations (read, write, append) are wrapped with `@retry_file_io` decorator (see Section 5.6) to handle temporary file locks, permission errors, and disk I/O issues. Retries up to 3 times with 1-second wait between attempts.

---

## 5. Supporting Modules

### 5.1 Unit Normalizer

**Module:** `core/unit_normalizer.py`

**Purpose:** Normalize unit strings and parse values for consistent comparison in the legacy fallback path and for display purposes.

**Capabilities:**

Unit alias resolution with 40+ mappings:

| Input Variants                 | Canonical Form |
|-------------------------------|----------------|
| %, % w/w, %w/w, wt%, percent | %              |
| ppm, mg/L, mg/kg             | ppm            |
| ppb, ug/L, ug/kg             | ppb            |
| g/cm3, g/cc                  | g/cm3          |
| SG, specific gravity         | SG             |
| NTU                          | NTU            |

Value parsing handles:
- Plain numeric values: "5.2" returns (5.2, "")
- Less-than qualifiers: "<0.5" returns (0.5, "less_than")
- Greater-than qualifiers: ">10" returns (10.0, "greater_than")
- Approximate qualifiers: "~3.0" returns (3.0, "approximately")
- Not detected: "ND", "BDL", "Not Detected" returns (0.0, "not_detected")
- Qualitative values: "Conforms", "Clear liquid" returns (None, "qualitative")
- Not applicable: "N/A", "-" returns (None, "not_applicable")

Unit conversion supports bidirectional conversion between compatible units using a factors table (mg/L to ppm = 1.0, g/L to ppm = 1000.0, ppb to ppm = 0.001, and so on).

### 5.2 Model Switcher

**Module:** `model_switcher.py`

**Purpose:** Provide a single point of control for selecting the LLM model, with support for CLI override.

**Model Selection Priority:**

1. Explicit override parameter passed programmatically
2. `--model` CLI argument (e.g., `python main.py --model gpt-4o-mini`)
3. `DEFAULT_MODEL` from the environment configuration file

**Available Models (ranked by capability):**

| Model        | Strengths                          | Recommended Use     |
|--------------|------------------------------------|---------------------|
| gpt-4o       | Best multimodal reasoning          | Production          |
| gpt-4.1      | Latest iteration                   | Testing             |
| gpt-4o-mini  | Cost-effective                     | Batch processing    |
| gpt-4-turbo  | Reliable fallback                  | When gpt-4o is down |

### 5.3 Configuration

**Module:** `config.py`

Central configuration loaded from a `.env` file using `python-dotenv`. All paths are resolved relative to the project root directory. Directory creation is handled at import time -- the data, logs, and output directories are created automatically if they do not exist.

**Environment Variables:**

| Variable       | Default   | Description                               |
|----------------|-----------|-------------------------------------------|
| OPENAI_API_KEY | (required)| OpenAI API key with GPT-4o access         |
| DEFAULT_MODEL  | gpt-4o    | Default model for all API calls           |
| TEMPERATURE    | 0         | LLM temperature (0 = deterministic)       |
| DATA_DIR       | data      | Directory for mapping file and organized PDFs |
| LOGS_DIR       | logs      | Directory for audit logs                  |
| OUTPUTS_DIR    | outputs   | Directory for extracted JSON files        |

### 5.4 Mapping Builder

**Module:** `build_mapping.py`

**Purpose:** Generate the `data/mapping.xlsx` file that maps each IXOM product to its associated specification and certificate PDF filenames.

The mapping contains 15 rows (products) across 3 industries. Each row specifies:

| Column          | Description                             |
|-----------------|-----------------------------------------|
| SN              | Serial number (1-15)                    |
| Industry        | Industry sector                         |
| Material_Number | IXOM material code                      |
| Spec_File       | Product specification PDF filename      |
| COA_File        | Certificate of Analysis PDF filename    |
| COCA_File       | Certificate of Compliance PDF filename  |
| COC_File        | Certificate of Conformance PDF filename |

Not every product has all three certificate types. Empty cells indicate that no certificate of that type exists for the product.

### 5.5 Schema Validation

**Module:** `core/schemas.py`

**Purpose:** Provide Pydantic-based data validation models to ensure data integrity throughout the extraction and comparison pipeline.

**Capabilities:**

The schema validation module defines seven Pydantic models that enforce type safety, value constraints, and structural consistency:

**Core Data Models:**

| Schema                      | Purpose                                    | Key Validations                                      |
|-----------------------------|-------------------------------------------|-----------------------------------------------------|
| ParameterSchema             | Individual parameter in spec/cert         | Non-empty name, confidence 0.0-1.0                  |
| ClassificationSchema        | Document type classification              | Valid doc_type enum, confidence bounds              |
| SpecificationSchema         | Complete specification extraction         | Parameter count matches list length                 |
| CertificateSchema           | Complete certificate extraction           | Parameter count matches list length                 |
| ComparisonSchema            | Overall validation result                 | Status enum, counts consistent with details         |
| ParameterComparisonSchema   | Single parameter comparison               | Status enum, at least one field present            |
| AuditLogSchema              | Audit trail entry                         | Valid timestamp, non-empty product name            |

**Validation Features:**

- **Type Enforcement:** All fields have explicit types (str, float, int, Optional, List, Enum)
- **Value Constraints:** Confidence scores bounded to [0.0, 1.0], counts must be non-negative
- **Structural Consistency:** Model validators ensure parameter counts match actual list lengths
- **Enum Safety:** Classification doc_type and comparison status use typed enums (no invalid strings)
- **Optional Field Handling:** Graceful handling of missing data (compliance_text, product_name, etc.)

**Integration Points:**

All extractors and the comparator use these schemas to validate their output before returning data:

```python
# Example from cert_extractor.py
validated_data = CertificateSchema(**parsed_data)
```

If validation fails, a `ValidationError` is raised with detailed field-level error messages, preventing corrupted data from propagating through the pipeline.

### 5.6 Retry Logic

**Module:** `core/retry_config.py`

**Purpose:** Provide resilient retry decorators for handling transient failures in API calls, file I/O, and PDF operations.

**Capabilities:**

Three specialized retry decorators using the `tenacity` library with exponential backoff:

**Retry Decorators:**

| Decorator             | Max Attempts | Backoff Strategy        | Target Failures                               |
|----------------------|--------------|------------------------|-----------------------------------------------|
| @retry_openai_call   | 3            | Exponential 1-10s      | RateLimitError, APIConnectionError, Timeout   |
| @retry_file_io       | 3            | Fixed 1s wait          | IOError, OSError, PermissionError             |
| @retry_pdf_operation | 2            | Fixed 2s wait          | All exceptions (PDF loading failures)         |

**Retry Features:**

- **Automatic Retry:** Transient failures trigger automatic retries without code changes
- **Exponential Backoff:** OpenAI calls use `2^x` second delays (1s, 2s, 4s) to handle rate limits
- **Comprehensive Logging:** Each retry attempt is logged with attempt number and exception details
- **Graceful Failure:** After exhausting retries, original exception is raised with full context

**Integration Points:**

Retry decorators are applied to all external dependency interactions across 7 core modules:

- **OpenAI API Calls:** cert_extractor (2 calls), spec_extractor (2 calls), document_classifier (1 call), comparator (1 call)
- **File I/O Operations:** cert_extractor (JSON save), spec_extractor (JSON save), logger (all CSV operations)
- **PDF Operations:** pdf_renderer (PDF loading), main.py (Excel reading)

**Example Usage:**

```python
@retry_openai_call
def call_openai_api(self, messages, response_format):
    return self.client.chat.completions.create(...)
```

This ensures production stability by automatically recovering from:
- OpenAI API rate limits (429 errors)
- Temporary network failures
- File system locks or permission issues
- Corrupted/inaccessible PDF files

---

## 6. User Interfaces

### 6.1 Streamlit Web Dashboard

**Module:** `ui.py`

The Streamlit application provides an interactive web interface with three tabs:

**Tab 1: Validate Certificate**

The primary workflow tab. The user selects an IXOM product specification from a dropdown (populated from `mapping.xlsx`), uploads a supplier certificate PDF, and clicks "Validate". The system runs the full pipeline (classify, extract, compare) and displays:

- Overall status badge (PASS, FAIL, REVIEW, ERROR)
- Product mismatch alert if the certificate is for a different product
- Summary metrics: parameters checked, passed, failed, review, not in cert
- Detailed failure/review reasons
- Compliance statement display for COCA/COC certificates
- Parameter-by-parameter comparison table with color-coded rows
- Expandable section showing full extracted JSON data

The comparison table uses dark-mode-compatible color coding:

| Status       | Background Color | Text Color |
|--------------|-----------------|------------|
| PASS         | Dark green      | Light green|
| FAIL         | Dark red        | Light red  |
| REVIEW       | Dark amber      | Light amber|
| NOT_IN_CERT  | Dark grey       | Grey       |

**Tab 2: Audit History**

Displays the persistent audit log as a filterable, sortable data table. Supports filtering by status, certificate type, and model. Each row can be expanded to inspect full details.

**Tab 3: Extracted Data Viewer**

Displays the raw extracted JSON files from the `outputs/structured_json/` directory. Useful for debugging extraction quality and verifying that the AI correctly read the PDF content.

### 6.2 CLI Batch Processor

**Module:** `main.py`

The command-line interface processes multiple specification-certificate pairs in batch mode. It reads the mapping file, iterates over each row and certificate type column, and calls `process_single_pair` for each valid pair.

**Usage:**

```
python main.py                        Process all 15 product rows
python main.py --golden-test          Process rows 1, 6, 11 only
python main.py --row 3                Process a specific row
python main.py --model gpt-4o-mini    Override model
```

The CLI prints progress to the console with status indicators and writes results to both the audit log and a per-run summary file.

---

## 7. Data Flow

### 7.1 Complete Data Flow for a Single Pair

The following describes the exact sequence of operations when validating one specification-certificate pair:

```
1.  main.py reads mapping.xlsx to get spec and cert filenames
2.  resolve_pdf_path() locates the PDF files on disk
3.  document_classifier reads cert PDF page 1
4.  pdf_renderer converts page 1 to base64 PNG at 200 DPI
5.  GPT-4o Vision classifies the document type (returns JSON)
6.  spec_extractor reads all pages of the spec PDF
7.  pdf_renderer converts all spec pages to base64 PNGs
8.  GPT-4o Vision extracts parameters from spec (returns JSON)
9.  Extracted spec JSON is saved to outputs/structured_json/
10. cert_extractor reads all pages of the cert PDF
11. pdf_renderer converts all cert pages to base64 PNGs
12. GPT-4o Vision extracts parameters from cert (returns JSON)
13. Extracted cert JSON is saved to outputs/structured_json/
14. comparator._check_product_match() runs token pre-check
15. If product mismatch detected: return FAIL immediately (skip AI)
16. comparator._ai_compare() sends spec + cert JSON to GPT-4o
17. GPT-4o aligns parameters by chemistry knowledge (returns JSON)
18. Status logic engine separates matched vs NOT_IN_CERT parameters
19. Overall status determined from matched parameters only
20. logger.log_result() appends to audit_log.csv
21. Result dict returned to caller (CLI or UI)
```

### 7.2 API Call Count Per Pair

| Stage           | API Calls | Model    | Purpose                    |
|-----------------|-----------|----------|----------------------------|
| Classification  | 1         | GPT-4o   | Document type detection    |
| Spec Extraction | 1         | GPT-4o   | Parameter extraction       |
| Cert Extraction | 1         | GPT-4o   | Parameter extraction       |
| AI Comparison   | 1         | GPT-4o   | Alignment and comparison   |
| **Total**       | **4**     |          | **Per specification-certificate pair** |

If the product mismatch pre-check detects an obvious mismatch, the comparison API call is skipped, reducing the total to 3.

### 7.3 JSON Output Examples

**Specification Extraction Output:**

```
{
  "document_type": "Product_Specification",
  "product_name": "Aluminium Sulphate Liquid",
  "material_number": "ALUSUL08-1000NR",
  "confidence_score": 0.95,
  "parameters": [
    {
      "name": "Aluminium content as Al2O3",
      "value": "",
      "unit": "%",
      "min_limit": "7.8",
      "max_limit": "8.2"
    },
    {
      "name": "pH",
      "value": "",
      "unit": "",
      "min_limit": "2.3",
      "max_limit": "2.8"
    },
    {
      "name": "Specific gravity",
      "value": "",
      "unit": "",
      "min_limit": "1.30",
      "max_limit": "1.32"
    }
  ]
}
```

**Comparison Output:**

```
{
  "status": "PASS",
  "reason": "All parameters within specification",
  "cert_type": "COA",
  "product_name": "Acetic Acid 20% - Premium Grade",
  "batch_number": "118541",
  "parameters_checked": 5,
  "parameters_passed": 3,
  "parameters_failed": 0,
  "parameters_review": 0,
  "parameters_not_in_cert": 2,
  "details": [
    {
      "parameter": "Strength (as Acetic Acid)",
      "cert_parameter": "Strength (Acetic Acid)",
      "spec_min": "19.5",
      "spec_max": "20.5",
      "cert_value": "20.0",
      "status": "PASS",
      "reason": "Value 20.0 within limits 19.5-20.5"
    },
    {
      "parameter": "Foreign Matter (Food safety risk)",
      "cert_parameter": "",
      "cert_value": "",
      "status": "NOT_IN_CERT",
      "reason": "Manufacturing-floor check, not in lab certificate"
    }
  ]
}
```

---

## 8. Status Definitions

### 8.1 Overall Document Status

| Status | Condition                                           | Required Action                  |
|--------|-----------------------------------------------------|----------------------------------|
| PASS   | All matched parameters within specification limits  | Accept certificate               |
| FAIL   | One or more values proven out of range, or product mismatch | Reject certificate       |
| REVIEW | Cannot determine compliance automatically           | Manual QA review required        |
| ERROR  | Processing failure (file not found, API error)      | Fix issue and re-process         |

### 8.2 Per-Parameter Status

| Status       | Condition                                                      |
|--------------|----------------------------------------------------------------|
| PASS         | Value within numeric limits, or qualitative match accepted     |
| FAIL         | Value mathematically proven outside specification limits       |
| REVIEW       | Uncertainty: incompatible units, temperature correction needed |
| NOT_IN_CERT  | Specification parameter has no counterpart in certificate      |

### 8.3 Status Determination Logic

The system applies a conservative hierarchy:

- FAIL is assigned only when arithmetic proves a value falls outside numeric limits. The system does not guess or estimate.
- PASS is assigned generously for qualitative parameters. Certificate values such as "Pass", "Conforms", "Complies", "Clear", "Clear and free of impurities" are all accepted as PASS against qualitative spec requirements.
- ND (Not Detected) for impurity parameters is always PASS when a maximum limit exists, because the absence of the impurity satisfies the requirement.
- REVIEW is the safe default for any situation where the system cannot determine compliance with certainty, including unit mismatches, temperature condition differences exceeding 2 degrees Celsius, and ranges instead of single values.
- NOT_IN_CERT is not a failure state. It indicates that the specification parameter is of a type that suppliers do not test (such as visual inspection for foreign matter on a manufacturing floor). These parameters require separate verification outside the scope of certificate validation.

---

## 9. Product Matching System

### 9.1 Why Product Matching is Needed

The same product appears under very different names in specifications versus certificates:

| Specification Name             | Certificate Name                                   |
|-------------------------------|----------------------------------------------------|
| Acetic Acid 20% - Premium Grade | ACETIC ACID 20% FLV10594 PREMIUM GRD 15L         |
| Aluminium Sulphate Liquid     | LIQUID ALUM NON RETURNABLE IBC (1310 KG)           |
| Aqua Ammonia 25%              | AQUEOUS AMMONIA 25% in Drums 190 kg                |
| Sodium Hypochlorite 13%       | SODIUM HYPO 13% 1000L IBC                          |
| Sodium Hydroxide 46%          | CAUSTIC SODA 46% LIQ                               |

Without product matching, the system would attempt to compare parameters between fundamentally different chemicals, producing meaningless results.

### 9.2 Three-Layer Matching Architecture

**Layer 1 (Token Pre-Check):** Fast, local, zero-cost. Catches obvious mismatches like "Acetic Acid" vs "Zinc Gluconate" where no tokens overlap at all. Uses abbreviation alias expansion and substring matching to handle cases like "LIQUID ALUM" matching "Aluminium Sulphate".

**Layer 2 (AI Verification):** If the token pre-check is uncertain, the full comparison prompt includes product matching instructions. GPT-4o uses chemical domain knowledge to make the final determination.

**Layer 3 (Short-Circuit):** If the token pre-check detects zero overlap, the system returns FAIL immediately without calling the AI, saving one API call per obviously wrong pair.

---

## 10. Certificate Type Handling

### 10.1 COA (Certificate of Analysis)

COA documents contain actual laboratory test results -- measured numeric values for one or more batches. The system extracts each measured value and compares it directly against specification limits. This is the most straightforward comparison type.

### 10.2 COCA (Certificate of Compliance with Analysis)

COCA documents are hybrid: they contain a compliance declaration (a signed statement that the product meets specifications) AND may also contain actual test data. The system extracts both the compliance statement text and all test parameters. If test data is present, each parameter is compared against specification limits the same way as a COA.

### 10.3 COC (Certificate of Conformance)

COC documents primarily contain a compliance statement. Some include specification ranges (e.g., "pH: 7.90-8.20") rather than individual tested values. The system:

- Extracts the compliance statement
- Extracts any ranges or values shown
- Compares ranges against spec limits: if the certificate range falls entirely within the spec range, the status is PASS; if it overlaps but extends beyond, REVIEW; if fully outside, FAIL

---

## 11. File System Layout

```
IXOM-POC/
    pdfs/                               Source PDF documents (34 files)
        Acetic Acid 20 Prem Grade Oct24.pdf
        ALUSUL08 Product Specification Nov 2022.pdf
        Aqua Ammonia 25 Prem Grade Aug 24.pdf
        ... (12 more spec files)
        000D3AD1FF1D1EEFBCA147C86F308999.pdf
        ... (18 more certificate files)
    intelligent_safety_net/             Project root
        .env                            API keys (git-ignored)
        config.py                       Central configuration
        main.py                         CLI batch processor
        ui.py                           Streamlit dashboard
        model_switcher.py               Model selection logic
        build_mapping.py                Mapping file generator
        requirements.txt                Python dependencies
        core/
            __init__.py
            pdf_renderer.py             PDF to image conversion
            document_classifier.py      Document type detection
            spec_extractor.py           Specification extraction
            cert_extractor.py           Certificate extraction
            comparator.py               AI comparison engine
            unit_normalizer.py          Unit and value parsing
            logger.py                   CSV audit logging
        data/
            mapping.xlsx                Product-document mapping
            specs/                      (reserved for organized specs)
            certificates/               (reserved for organized certs)
        outputs/
            structured_json/            Extracted JSON files
        logs/
            audit_log.csv               Persistent audit trail
            run_summary_*.csv           Per-run summaries
```

---

## 12. Performance Characteristics

### 12.1 Processing Time

| Operation                   | Typical Duration |
|-----------------------------|-----------------|
| PDF rendering (1 page)      | Under 1 second  |
| Document classification     | 3-5 seconds     |
| Specification extraction    | 15-30 seconds   |
| Certificate extraction      | 10-20 seconds   |
| AI comparison               | 5-10 seconds    |
| Single pair end-to-end      | 30-60 seconds   |
| Golden test (5 pairs)       | 4-5 minutes     |
| Full batch (15 products)    | 15-20 minutes   |

### 12.2 API Cost

| Operation             | Approximate Cost (USD) |
|-----------------------|-----------------------|
| Single pair           | 0.05-0.15             |
| Golden test (5 pairs) | 0.25-0.75             |
| Full batch            | 0.75-2.25             |

Costs depend on document page count and parameter count. Multi-page specifications with many parameters consume more tokens.

### 12.3 Accuracy (Golden Test Results)

| Pair                       | Expected | Actual | Notes                           |
|----------------------------|----------|--------|---------------------------------|
| Acetic Acid vs COA         | PASS     | PASS   | All 3 matched params within spec|
| Acetic Acid vs COCA        | PASS     | PASS   | Compliance + 3 params pass      |
| Aqua Ammonia vs COA        | REVIEW   | REVIEW | Density at different temperature|
| Alum Sulphate vs COA       | PASS     | PASS   | pH and SG within limits         |
| Alum Sulphate vs COC       | PASS     | PASS   | All params within spec ranges   |

The Aqua Ammonia REVIEW is a legitimate finding: the specification defines density at 15 degrees Celsius (0.907-0.913) but the certificate reports density 0.901 at 26.6 degrees Celsius. Temperature correction is required, which the system correctly flags for manual review.

---

## 13. Error Handling

### 13.1 API Failures

If the OpenAI API call fails during comparison, the system falls back to the legacy name-based matching algorithm. This produces lower accuracy but prevents complete pipeline failure. API failures during classification or extraction cause an ERROR status to be logged.

### 13.2 PDF Rendering Failures

If pypdfium2 cannot open a PDF (corrupted file, password-protected), a ValueError is raised and caught by the orchestrator, which logs an ERROR status.

### 13.3 JSON Parse Failures

All LLM responses use `response_format: json_object` to enforce valid JSON output. If the response still fails to parse (edge case), the system creates a default result with empty parameters and an error message.

### 13.4 File Not Found

The `resolve_pdf_path` function checks multiple locations (organized data directories first, then the source pdfs folder). If no file is found, an ERROR is logged and the pair is skipped.

---

## 14. Security Considerations

- The OpenAI API key is stored in a `.env` file that is excluded from version control via `.gitignore`.
- PDF documents are processed locally; only rendered images (base64 PNGs) are sent to the OpenAI API.
- The audit log is append-only and stored locally.
- No authentication is implemented on the Streamlit dashboard (appropriate for internal PoC use behind a corporate network).

---

## 15. Limitations and Known Constraints

1. The system requires an active internet connection for OpenAI API access. It cannot operate offline.
2. Temperature correction for density/SG measurements is flagged for manual review rather than computed automatically. A density correction table could be added in a future phase.
3. The product matching alias dictionary is manually maintained. New chemical abbreviations encountered in supplier certificates must be added to the `_CHEM_ALIASES` dictionary.
4. The system processes one pair at a time. Concurrent processing of multiple pairs is not implemented (rate limiting considerations with the OpenAI API).
5. Maximum 10 pages per document. Longer specifications (uncommon in practice) would have their later pages truncated.
6. The system validates parameter values against specification limits but does not validate certificate authenticity (signatures, dates, accreditation).

---

## 16. Dependencies

**Python Packages (requirements.txt):**

| Package          | Version | Purpose                                  |
|------------------|---------|------------------------------------------|
| openai           | 1.0+    | OpenAI API client                        |
| pandas           | 2.0+    | Data handling, mapping file              |
| openpyxl         | 3.1+    | Excel file reading                       |
| pypdfium2        | Latest  | PDF rendering (pure Python)              |
| Pillow           | 10.0+   | Image processing                         |
| python-dotenv    | 1.0+    | Environment variable loading             |
| streamlit        | 1.30+   | Web dashboard                            |

**External Dependencies:** None. pypdfium2 bundles the PDFium binary as a Python wheel, eliminating the need for Poppler or other system-level PDF libraries.

---

## 17. Glossary

| Term                   | Definition                                                                        |
|------------------------|-----------------------------------------------------------------------------------|
| COA                    | Certificate of Analysis: lab report with measured test values for a product batch  |
| COCA                   | Certificate of Compliance with Analysis: compliance statement plus optional test data |
| COC                    | Certificate of Conformance: signed statement that product meets specifications     |
| Specification (Spec)   | IXOM internal document defining acceptable parameter ranges for a product          |
| Parameter              | A measurable or observable property (e.g., pH, strength, appearance)               |
| Min Limit              | Lower acceptable boundary for a numeric parameter                                  |
| Max Limit              | Upper acceptable boundary for a numeric parameter                                  |
| ND (Not Detected)      | Lab result indicating the substance was below the detection limit                  |
| SG                     | Specific Gravity: ratio of substance density to water density                      |
| DPI                    | Dots Per Inch: image rendering resolution                                          |
| Token Pre-Check        | Fast local product matching using word overlap without AI                          |
| Alias Expansion        | Replacing chemical abbreviations with canonical names for matching                 |
| Golden Test            | Predefined set of known-correct pairs used for validation                          |
| NOT_IN_CERT            | Status indicating a spec parameter has no corresponding test in the certificate    |
