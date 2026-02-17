# 🛡️ Intelligent Safety Net — IXOM Product Safety Verification Engine

> **Phase 0 — Proof of Concept**

A standalone AI-powered validation engine that compares supplier certificates (COA/COCA/COC) against IXOM product specifications using GPT-4o Vision. The system automatically reads PDF documents, extracts structured chemical parameters, and validates compliance — replacing manual, error-prone human review.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Pipeline Flow](#pipeline-flow)
- [Project Structure](#project-structure)
- [Module Reference](#module-reference)
- [Certificate Types](#certificate-types)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Configuration](#configuration)
- [Golden Test](#golden-test)
- [Status Definitions](#status-definitions)
- [Product Matching](#product-matching)
- [Key Design Decisions](#key-design-decisions)
- [Data & Document Mapping](#data--document-mapping)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Problem

IXOM receives supplier certificates (Certificates of Analysis, Compliance, and Conformance) for every batch of raw material or finished product. Quality Assurance teams must manually compare each certificate's test results against IXOM's internal product specifications to verify compliance. This process is:

- **Time-consuming** — each comparison takes 10-30 minutes
- **Error-prone** — parameter names differ between suppliers and specs
- **Inconsistent** — different analysts may interpret results differently
- **Unscalable** — 15+ products × 3 industries × multiple cert types

### Solution

The Intelligent Safety Net automates this entire workflow:

1. **Upload** a supplier certificate PDF
2. **AI classifies** the document type (COA / COCA / COC)
3. **AI extracts** all test parameters from both spec and cert
4. **AI aligns** differently-named parameters using chemistry knowledge
5. **AI compares** values against specification limits
6. **System returns** Pass ✅ / Fail ❌ / Review 🔍 with parameter-level detail

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENT SAFETY NET                       │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   PDF    │    │   Document   │    │     Spec     │              │
│  │ Renderer │───▶│  Classifier  │    │  Extractor   │              │
│  │(pypdfium)│    │  (GPT-4o)    │    │  (GPT-4o)    │              │
│  └──────────┘    └──────┬───────┘    └──────┬───────┘              │
│       │                 │                    │                      │
│       │          ┌──────▼───────┐            │                      │
│       └─────────▶│ Certificate  │            │                      │
│                  │  Extractor   │            │                      │
│                  │  (GPT-4o)    │            │                      │
│                  └──────┬───────┘            │                      │
│                         │                    │                      │
│                  ┌──────▼────────────────────▼──┐                  │
│                  │       AI COMPARATOR          │                  │
│                  │  ┌─────────────────────────┐ │                  │
│                  │  │  Product Match Check    │ │                  │
│                  │  │  (Token + Alias Engine) │ │                  │
│                  │  └────────────┬────────────┘ │                  │
│                  │  ┌────────────▼────────────┐ │                  │
│                  │  │  GPT-4o AI Alignment    │ │                  │
│                  │  │  & Value Comparison     │ │                  │
│                  │  └────────────┬────────────┘ │                  │
│                  │  ┌────────────▼────────────┐ │                  │
│                  │  │  Status Logic Engine    │ │                  │
│                  │  │ PASS/FAIL/REVIEW/NOT_IN │ │                  │
│                  │  └─────────────────────────┘ │                  │
│                  └──────────────┬───────────────┘                  │
│                                │                                    │
│                  ┌─────────────▼─────────────┐                     │
│                  │     Audit Logger (CSV)     │                     │
│                  └───────────────────────────┘                     │
│                                                                     │
│  ┌──────────────────────────────────────────┐                      │
│  │         Streamlit Dashboard (UI)         │                      │
│  │  Tab 1: Interactive Validation           │                      │
│  │  Tab 2: Audit History                    │                      │
│  │  Tab 3: Extracted Data Viewer            │                      │
│  └──────────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **AI/LLM** | OpenAI GPT-4o (Vision) | Document classification, parameter extraction, intelligent comparison |
| **PDF Rendering** | pypdfium2 + Pillow | Pure-Python PDF → image conversion (no Poppler dependency) |
| **Backend** | Python 3.10+ | Core pipeline orchestration |
| **Frontend** | Streamlit | Interactive demo dashboard |
| **Data** | pandas + openpyxl | Mapping file, audit logs, structured outputs |
| **Config** | python-dotenv | Environment variable management |

---

## Pipeline Flow

Each spec ↔ certificate pair goes through a **5-stage pipeline**:

```
PDF File ──▶ Stage 1: Render ──▶ Stage 2: Classify ──▶ Stage 3: Extract ──▶ Stage 4: Compare ──▶ Stage 5: Log
```

### Stage 1 — PDF Rendering (`core/pdf_renderer.py`)

Converts PDF pages to base64-encoded PNG images at 200 DPI using `pypdfium2`.

- **Input**: PDF file path
- **Output**: List of base64 PNG strings (one per page)
- **Settings**: DPI=200, max size 2048×2048, max 10 pages per document
- **No external binaries required** — pure Python, cross-platform

### Stage 2 — Document Classification (`core/document_classifier.py`)

Sends the **first page** image to GPT-4o Vision to classify the document type.

- **Input**: First page image (base64)
- **Output**: `{ document_type, confidence_score, product_name, reasoning }`
- **Categories**: `Product_Specification` | `COA` | `COCA` | `COC` | `Invoice` | `Other`
- **Typical confidence**: 0.95

### Stage 3 — Parameter Extraction

Two separate extractors handle specs and certificates:

#### Spec Extractor (`core/spec_extractor.py`)
- Sends **all pages** to GPT-4o Vision
- Extracts: product name, material number, and all parameters with min/max limits
- Handles multi-grade specs (extracts primary grade only, no duplicates)
- **Output schema**:
  ```json
  {
    "product_name": "Acetic Acid 20% - Premium Grade",
    "material_number": "ACEACI20FG-1000L",
    "parameters": [
      {
        "name": "Strength (as Acetic Acid)",
        "value": "",
        "unit": "% w/w",
        "min_limit": "19.5",
        "max_limit": "20.5"
      }
    ]
  }
  ```

#### Certificate Extractor (`core/cert_extractor.py`)
- Uses **type-specific prompts** for COA vs COCA/COC
- COA prompt: Focuses on lab test results, standardized naming
- COCA/COC prompt: Extracts both compliance statement AND test parameters
- **Output schema** includes: product_name, batch_number, supplier_name, compliance_statement, parameters

### Stage 4 — AI-Powered Comparison (`core/comparator.py`)

The most sophisticated component — a **three-layer comparison engine**:

#### Layer 1: Product Mismatch Pre-Check (Token Engine)
Fast, local check using token overlap + chemical abbreviation aliases:
- `alum` ↔ `aluminium`, `hypo` ↔ `hypochlorite`, `caustic` ↔ `hydroxide`, etc.
- Includes substring matching (`alum` ⊂ `aluminium`)
- Only flags obvious mismatches (zero overlap between completely different chemicals)
- Passes uncertain cases to AI for final decision

#### Layer 2: GPT-4o AI Alignment & Comparison
- Aligns differently-named parameters using chemistry knowledge
- Examples: `"Strength (as Acetic Acid)"` = `"Acid Strength (%w/w Acetic)"`
- Handles SG temperature notation: `SG (20/4)` = `SG (20°C)` = `SG (20/4°C)`
- Performs numeric comparison against spec limits
- Returns per-parameter status with reasoning

#### Layer 3: Status Logic Engine
- Separates **matched parameters** from **NOT_IN_CERT** parameters
- Overall PASS if all matched parameters pass (NOT_IN_CERT doesn't affect verdict)
- Overall FAIL only if any parameter is mathematically proven out of range
- Overall REVIEW for uncertainties (temperature corrections, missing data)

### Stage 5 — Audit Logging (`core/logger.py`)

- Appends every result to `logs/audit_log.csv` (persistent)
- Creates per-run summaries in `logs/run_summary_YYYYMMDD_HHMMSS.csv`
- Tracks: timestamp, files, status, parameters checked/passed/failed/review, reason

---

## Project Structure

```
intelligent_safety_net/
├── .env                          # API keys and environment config
├── .gitignore                    # Git ignore rules
├── config.py                     # Central configuration (paths, DPI, models)
├── main.py                       # CLI batch orchestrator
├── ui.py                         # Streamlit interactive dashboard
├── model_switcher.py             # Multi-model support (gpt-4o, gpt-4o-mini, etc.)
├── build_mapping.py              # Generates data/mapping.xlsx
├── requirements.txt              # Python dependencies
├── README.md                     # This file
│
├── core/                         # Core engine modules
│   ├── __init__.py
│   ├── pdf_renderer.py           # PDF → base64 image conversion (pypdfium2)
│   ├── document_classifier.py    # AI document type classification
│   ├── spec_extractor.py         # Product specification parameter extraction
│   ├── cert_extractor.py         # Certificate (COA/COCA/COC) data extraction
│   ├── comparator.py             # AI-powered parameter alignment & comparison
│   ├── unit_normalizer.py        # Unit conversion & value parsing
│   └── logger.py                 # CSV audit logging
│
├── data/                         # Data files
│   ├── mapping.xlsx              # Product ↔ document mapping (15 rows)
│   ├── specs/                    # (optional) organized spec PDFs
│   └── certificates/             # (optional) organized certificate PDFs
│
├── outputs/
│   └── structured_json/          # Extracted JSON files from GPT-4o
│
└── logs/
    ├── audit_log.csv             # Persistent audit trail
    └── run_summary_*.csv         # Per-run summaries
```

### Source PDFs

The raw PDF documents are stored in `../pdfs/` (one level above the project):

- **15 named spec files** (e.g., `Acetic Acid 20 Prem Grade Oct24.pdf`)
- **19 GUID-named certificate files** (e.g., `000D3AD1FF1D1EEFBCA147C86F308999.pdf`)

---

## Module Reference

### `config.py`
Central configuration loaded from `.env` file with sensible defaults.

| Setting | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | (from .env) | OpenAI API key |
| `DEFAULT_MODEL` | `gpt-4o` | Default LLM model |
| `TEMPERATURE` | `0` | LLM temperature (deterministic) |
| `IMAGE_DPI` | `200` | PDF rendering resolution |
| `MAX_IMAGE_SIZE` | `(2048, 2048)` | Max image dimensions for API |
| `MAX_PAGES_PER_DOC` | `10` | Max pages sent to Vision API |
| `GOLDEN_TEST_ROWS` | `[1, 6, 11]` | Row indices for golden test |

### `core/pdf_renderer.py`
| Function | Description |
|----------|-------------|
| `pdf_page_to_base64(path, page_num, dpi)` | Convert single page to base64 PNG |
| `pdf_to_base64_images(path, dpi, max_pages)` | Convert all pages to base64 PNG list |
| `get_page_count(path)` | Get page count of a PDF |

### `core/document_classifier.py`
| Function | Description |
|----------|-------------|
| `classify_document(pdf_path, model)` | Classify PDF type using first page |

### `core/spec_extractor.py`
| Function | Description |
|----------|-------------|
| `extract_spec(pdf_path, model)` | Extract parameters from a product specification |

### `core/cert_extractor.py`
| Function | Description |
|----------|-------------|
| `extract_certificate(pdf_path, model, expected_type)` | Extract data from COA/COCA/COC |

### `core/comparator.py`
| Function | Description |
|----------|-------------|
| `compare_documents(spec_data, cert_data, cert_type, model)` | Full AI-powered comparison |
| `_check_product_match(spec_product, cert_product)` | Token-based product mismatch pre-check |
| `_ai_compare(spec_data, cert_data, cert_type, model)` | GPT-4o parameter alignment |

### `core/unit_normalizer.py`
| Function | Description |
|----------|-------------|
| `normalize_unit(unit)` | Canonicalize unit strings (`%w/w` → `%`) |
| `normalize_param_name(name)` | Lowercase + strip special chars |
| `parse_value(value_str)` | Parse numeric/qualitative/ND values |
| `are_units_compatible(u1, u2)` | Check if two units can be converted |
| `convert_value(value, from_unit, to_unit)` | Unit conversion |

### `core/logger.py`
| Function | Description |
|----------|-------------|
| `log_result(...)` | Append comparison result to audit CSV |
| `log_error(...)` | Log processing errors |
| `write_run_summary(results, model)` | Write per-run summary CSV |
| `print_summary(results)` | Print summary to console |

### `model_switcher.py`
| Function | Description |
|----------|-------------|
| `get_model(override)` | Get model by priority: override → CLI → config |
| `list_models()` | List available models |

---

## Certificate Types

| Type | Full Name | Contents | How System Handles |
|------|-----------|----------|-------------------|
| **COA** | Certificate of Analysis | Lab test results with measured values | Compare each value against spec limits |
| **COCA** | Certificate of Compliance with Analysis | Compliance declaration + test data | Extract both statement and values; compare all |
| **COC** | Certificate of Conformance | Compliance statement, may include spec ranges | Compare ranges; note compliance statement |

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **OpenAI API key** with access to `gpt-4o` (Vision model)

### Installation

```bash
# 1. Clone or navigate to the project
cd d:\IXOM-POC\intelligent_safety_net

# 2. Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt
pip install pypdfium2      # Pure-Python PDF renderer (replaces poppler)

# 4. Set up environment variables
# Create .env file with:
echo OPENAI_API_KEY=sk-your-key-here > .env
echo DEFAULT_MODEL=gpt-4o >> .env
echo TEMPERATURE=0 >> .env

# 5. Generate the mapping file
python build_mapping.py
```

### Verify Installation

```bash
python -c "import pypdfium2, openai, streamlit, pandas; print('All dependencies OK')"
```

---

## Usage

### 1. Streamlit Interactive UI

```bash
cd d:\IXOM-POC\intelligent_safety_net
streamlit run ui.py
```

Opens at **http://localhost:8501** with three tabs:

| Tab | Description |
|-----|-------------|
| **🔍 Validate Certificate** | Upload a cert PDF, select a product spec, run AI comparison |
| **📊 Audit History** | Browse all past validation results with filters |
| **📋 Extracted Data** | View extracted JSON from specs and certificates |

### 2. CLI Batch Processing

```bash
# Process all 15 product rows (all cert types)
python main.py

# Golden test — 3 representative rows (rows 1, 6, 11)
python main.py --golden-test

# Process a specific product row
python main.py --row 3

# Override model
python main.py --golden-test --model gpt-4o-mini

# Combine flags
python main.py --row 1 --model gpt-4.1
```

### 3. Individual Module Testing

```bash
# Classify a document
python -m core.document_classifier path/to/document.pdf

# Extract specification
python -m core.spec_extractor path/to/spec.pdf

# Extract certificate
python -m core.cert_extractor path/to/cert.pdf COA
```

---

## Configuration

### Environment Variables (`.env`)

```env
OPENAI_API_KEY=sk-proj-xxxxx
DEFAULT_MODEL=gpt-4o
TEMPERATURE=0
DATA_DIR=data
LOGS_DIR=logs
OUTPUTS_DIR=outputs
```

### Available Models

| Model | Strengths | Use Case |
|-------|-----------|----------|
| `gpt-4o` | Best multimodal + reasoning | Production / accuracy-critical |
| `gpt-4.1` | Latest iteration | Testing new capabilities |
| `gpt-4o-mini` | Cost-effective | Batch processing / budget |
| `gpt-4-turbo` | Reliable fallback | When gpt-4o unavailable |

---

## Golden Test

The golden test validates the pipeline against **3 representative products** across all 3 industries:

| Row | Product | Industry | Cert Types |
|-----|---------|----------|------------|
| 1 | Acetic Acid 20% Premium Grade | Food, Beverage & Nutrition | COA + COCA |
| 6 | Aqua Ammonia 25% Premium Grade | Health & Personal Care | COA |
| 11 | Aluminium Sulphate Liquid | Water | COA + COC |

**Expected results** (5 pairs total):

| Pair | Expected | Notes |
|------|----------|-------|
| Acetic Acid ↔ COA | ✅ PASS | Strength, SG, Appearance all within limits |
| Acetic Acid ↔ COCA | ✅ PASS | Compliance statement + test data both valid |
| Aqua Ammonia ↔ COA | 🔍 REVIEW | Density at different temperature requires manual verification |
| Alum Sulphate ↔ COA | ✅ PASS | pH and SG within limits |
| Alum Sulphate ↔ COC | ✅ PASS | All parameters within spec ranges |

```bash
python main.py --golden-test --model gpt-4o
```

---

## Status Definitions

### Overall Document Status

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ **PASS** | All matched parameters within specification | Accept certificate |
| ❌ **FAIL** | One or more values proven out of range, OR product mismatch | Reject certificate |
| 🔍 **REVIEW** | Uncertainty — cannot determine compliance automatically | Manual QA review needed |
| ⚠️ **ERROR** | Processing failure (file not found, API error, etc.) | Fix and re-process |

### Per-Parameter Status

| Status | Meaning |
|--------|---------|
| **PASS** | Value within spec limits, or qualitative match (Pass/Conforms/ND) |
| **FAIL** | Value mathematically proven outside spec limits |
| **REVIEW** | Cannot determine — units differ, temperature correction needed, ambiguous |
| **NOT_IN_CERT** | Spec parameter has no corresponding test in the certificate (e.g., visual inspection items) |

> **Key principle**: `NOT_IN_CERT` parameters do **not** affect the overall status. A document can be PASS even if some spec parameters aren't tested in the cert. Only matched parameters determine the verdict.

---

## Product Matching

The system detects when a certificate is for a **different product** than the specification.

### How It Works

1. **Token-based pre-check** — Fast, local comparison using:
   - Token overlap between product names
   - Chemical abbreviation aliases (40+ mappings)
   - Substring matching for abbreviated names
   - Concentration number matching

2. **AI verification** — GPT-4o confirms product identity using chemistry knowledge

### Abbreviation Aliases

| Alias | Canonical | Example |
|-------|-----------|---------|
| `alum` | `aluminium` | "LIQUID ALUM" = "Aluminium Sulphate Liquid" |
| `hypo` | `hypochlorite` | "SODIUM HYPO 13%" = "Sodium Hypochlorite 13%" |
| `caustic` | `hydroxide` | "CAUSTIC SODA 46%" = "Sodium Hydroxide 46%" |
| `hcl` | `hydrochloric` | "HCL 33% BULK" = "Hydrochloric Acid 33%" |
| `aqueous` | `aqua` | "AQUEOUS AMMONIA" = "Aqua Ammonia" |
| `sulphate` | `sulfate` | British/American spelling equivalence |

---

## Key Design Decisions

### 1. AI-First Approach
Parameter names **always** differ between specs and certs. String matching fails. GPT-4o uses chemistry knowledge to align parameters like `"Strength (as Acetic Acid)"` with `"Acid Strength (%w/w Acetic)"`.

### 2. Strict on FAIL, Generous on PASS
- **FAIL** requires mathematical proof (value outside numeric limits)
- **PASS** is generous for qualitative matches ("Pass", "Conforms", "Clear" all accepted)
- **REVIEW** is the safe default for any uncertainty

### 3. NOT_IN_CERT Separation
Visual inspection items (Foreign Matter, etc.) appear in specs but never in lab certs. These are marked `NOT_IN_CERT` and excluded from the overall verdict, preventing false `REVIEW` inflation.

### 4. Temperature-Aware SG Comparison
Specific Gravity varies with temperature. The system:
- Treats `SG (20/4)` = `SG (20°C)` = `SG (20/4°C)` as the same measurement
- Flags genuine temperature differences (>2°C gap) as REVIEW, not FAIL

### 5. Pure-Python PDF Rendering
Uses `pypdfium2` instead of `pdf2image` + Poppler, eliminating the need for external binary installations. Works on Windows, macOS, and Linux without additional setup.

### 6. Three-Layer Product Matching
Fast local pre-check catches obvious mismatches (zero API cost), while AI handles edge cases. This prevents sending wrong-product pairs through the expensive comparison pipeline.

---

## Data & Document Mapping

### Industries Covered

| Industry | Products |
|----------|----------|
| **Food, Beverage & Nutrition** | Acetic Acid 20%, Acetic Acid 80%, Aqua Ammonia 25%, Peanut Oil, Zinc Gluconate |
| **Health & Personal Care** | Aqua Ammonia 25%, Sodium Hypochlorite 13%, Solipac, Rezolv 25, Omega Max |
| **Water** | Aluminium Sulphate, PAC10LB, Sodium Hypochlorite 13%, Toflanat, Zydox 31 |

### Mapping File (`data/mapping.xlsx`)

| Column | Description |
|--------|-------------|
| `SN` | Serial number (1-15) |
| `Industry` | Industry sector |
| `Material_Number` | IXOM material code |
| `Spec_File` | Product specification PDF filename |
| `COA_File` | Certificate of Analysis PDF filename |
| `COCA_File` | Certificate of Compliance/Analysis PDF filename |
| `COC_File` | Certificate of Conformance PDF filename |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `streamlit: command not found` | `pip install streamlit` or `python -m streamlit run ui.py` |
| `ModuleNotFoundError: pypdfium2` | `pip install pypdfium2` |
| `OpenAI API error 401` | Check `.env` has valid `OPENAI_API_KEY` |
| `Mapping file not found` | Run `python build_mapping.py` |
| `PDF file not found` | Ensure `../pdfs/` folder contains all PDF documents |
| All results showing REVIEW | Clear `outputs/structured_json/*.json` and re-run |
| Product mismatch false positive | Check `_CHEM_ALIASES` in `comparator.py`, add missing aliases |

### Performance

| Metric | Typical Value |
|--------|--------------|
| Single pair (classify + extract + compare) | 30-60 seconds |
| Golden test (5 pairs) | ~4-5 minutes |
| Full batch (15 products, all cert types) | ~15-20 minutes |
| API cost per pair | ~$0.05-0.15 (GPT-4o Vision) |

### Clearing Cache

```bash
# Clear extracted JSONs (forces re-extraction)
Remove-Item outputs\structured_json\*.json -Force     # PowerShell
# rm outputs/structured_json/*.json                    # bash

# Clear audit logs
Remove-Item logs\*.csv -Force
```

---

## License

Internal IXOM use only — Phase 0 Proof of Concept.

---

*Built with GPT-4o Vision, Python 3.10, Streamlit, and pypdfium2*