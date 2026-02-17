# Intelligent Document Verification — UI Guide

> Complete reference for the Streamlit-based demo dashboard.

---

## Overview

The UI is a single-page **Streamlit** web application (`ui.py`) that lets users upload two PDF documents — a **Product Specification** and a **Supplier Certificate** — and runs an end-to-end AI-powered validation pipeline. All processing happens server-side using OpenAI GPT-4o Vision. The interface is designed for live demo use: minimal clicks, clean layout, no configuration required.

**Launch command:**

```bash
cd intelligent_safety_net
streamlit run ui.py
```

Default URL: `http://localhost:8501`

---

## Application Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    HERO HEADER                                 │
│  Title: INTELLIGENT DOCUMENT VERIFICATION                     │
│  Subtitle: Automated Supplier Certificate Validation Engine   │
│  Pipeline pills: ① Upload → ② Classify → ③ Extract → ④ Check │
└────────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────┐
    │ Tab: Validate   │         │ Tab: Audit       │
    │   Certificate   │         │   History        │
    └────────┬────────┘         └────────┬────────┘
             │                           │
             ▼                           ▼
     Upload 2 PDFs               View past results
             │                   Filter by status/type
             ▼                   Metric summary cards
     Click "Validate"            Scrollable data table
             │
             ▼
    ┌────────────────────────────────────────┐
    │         PROGRESS BAR (single bar)      │
    │  "Classifying document..."       25%   │
    │  "Extracting spec parameters..." 50%   │
    │  "Extracting certificate data.." 75%   │
    │  "Running compliance check..."   100%  │
    └────────────────────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────────┐
    │           FINAL REPORT                 │
    │  • Overall result banner (PASS/FAIL)   │
    │  • Product & certificate summary       │
    │  • Reason (if not PASS)                │
    │  • Metric cards (Pass/Fail/Review/NIC) │
    │  • Parameter details table             │
    │  • Critical issues section             │
    │  • Items for review section            │
    └────────────────────────────────────────┘
```

---

## Tab 1: Validate Certificate

### 1. Document Upload

Two side-by-side upload zones:

| Column | Label | Accepts | Purpose |
|--------|-------|---------|---------|
| Left | **Product Specification** | PDF | The internal spec defining acceptable parameter ranges |
| Right | **Supplier Certificate** | PDF | The supplier-provided COA / COCA / COC to validate |

- Drag-and-drop or browse
- After upload, a green confirmation bar shows the filename
- Both files must be uploaded before the Validate button appears
- If files are missing, a "Getting Started" prompt is shown instead

### 2. Validate Button

A full-width gradient blue button: **"Validate Certificate"**

Clicking it triggers the 4-step AI pipeline with a single progress bar.

### 3. Processing Pipeline

A **single progress bar** with inline status text cycles through four stages:

| Step | Progress | Status Text | Backend Function |
|------|----------|-------------|------------------|
| 1 | 0→25% | "Classifying document..." | `classify_document(cert_path, model)` |
| 2 | 25→50% | "Extracting specification parameters..." | `extract_spec(spec_path, model)` |
| 3 | 50→75% | "Extracting certificate data..." | `extract_certificate(cert_path, model, expected_type)` |
| 4 | 75→100% | "Running compliance check..." | `compare_documents(spec_data, cert_data, cert_type, model)` |

The progress bar auto-clears after completion — no lingering UI clutter.

### 4. Final Report

Once processing completes, the report renders in this order:

#### a) Overall Result Banner

A full-width colored banner showing:

- **Overall Result:** PASS / FAIL / REVIEW
- **Certificate Type:** COA / COCA / COC (auto-detected)
- **Confidence:** Classification confidence (e.g. 95%)
- **Time:** Total processing time (e.g. 171.1s)

Color coding:
- **Green** = PASS
- **Red** = FAIL
- **Amber/Yellow** = REVIEW

#### b) Summary Line

An info panel with:
- Product name (from spec)
- Certificate product name
- Number of spec parameters extracted
- Number of cert parameters extracted

#### c) Reason

If the result is not a clean PASS, a warning panel shows the reason string from the comparator (e.g. "Not in cert: Turbidity, Colour" or "Product mismatch detected").

#### d) Metric Cards

Four cards in a row:

| Card | Description |
|------|-------------|
| **PASSED** | Parameters that matched within spec limits |
| **FAILED** | Parameters outside spec limits |
| **REVIEW** | Parameters needing manual review |
| **NOT IN CERT** | Spec parameters not found in the certificate |

#### e) Parameter Details Table

A styled HTML table with columns:

| Column | Source |
|--------|--------|
| **Status** | Color-coded badge (PASS/FAIL/REVIEW/NOT_IN_CERT) |
| **Parameter** | Parameter name |
| **Spec Range** | Built from `spec_min` / `spec_max` (e.g. "5.0 – 7.0" or "Max 0.5") |
| **Spec Value** | Target/typical value from spec |
| **Cert Value** | Measured value from certificate |
| **Reason** | Explanation from AI comparison |

Rows highlight on hover.

#### f) Critical Issues

Red alert panels for each FAIL parameter:
- Shows parameter name, spec vs cert values, and reason

#### g) Items for Review

Amber alert panels for each REVIEW parameter:
- Shows parameter name and reason

### 5. Audit Logging

After every validation, the result is automatically logged to `logs/audit_log.csv` via `log_result()`. This happens silently — errors are suppressed so the UI never breaks.

---

## Tab 2: Audit History

### Filters

Two dropdowns at the top:

| Filter | Options |
|--------|---------|
| **Filter by Status** | ALL, PASS, FAIL, REVIEW |
| **Filter by Cert Type** | ALL, COA, COCA, COC |

### Metrics

Four summary cards: **TOTAL**, **PASSED**, **FAILED**, **REVIEW** — counts update based on active filters.

### Data Table

A full-width Streamlit dataframe showing all logged audit records. The **Model** column is auto-removed for cleanliness. Displays row count ("Showing X of Y records").

---

## UI Design Details

### Layout

- **Wide layout** — uses full browser width (max 1200px centered)
- **No sidebar** — hidden via CSS
- **No Streamlit chrome** — hamburger menu, footer, and header are all hidden
- **Two tabs only** — Validate Certificate + Audit History

### Color Palette

| Element | Color |
|---------|-------|
| Hero background | Dark navy gradient (`#0a1628` → `#2a5a8c`) |
| Pipeline pills | Blue translucent (`rgba(59,130,246,0.15)`) |
| PASS badge | Green gradient (`#065f46` → `#047857`) |
| FAIL badge | Red gradient (`#7f1d1d` → `#991b1b`) |
| REVIEW badge | Amber gradient (`#78350f` → `#92400e`) |
| Buttons | Blue gradient (`#1e40af` → `#3b82f6`) |
| Cards | Dark translucent (`rgba(15,23,42,0.6)`) |
| Text (primary) | Light gray (`#e2e8f0`) |
| Text (secondary) | Muted gray (`#94a3b8`) |

### Typography

- Title: 1.6rem, 700 weight, 1.5px letter-spacing
- Subtitle: 0.85rem, muted gray
- Section headers: 1.1rem, 600 weight, blue underline
- Body/table text: 0.82–0.85rem
- Metric values: 1.5rem, 700 weight

### Spacing

- Aggressive gap reduction on all Streamlit vertical blocks (0.15rem)
- File uploader labels hidden (CSS `display:none`)
- Upload confirmation bars have minimal top margin (0.35rem)
- No padding waste between elements

---

## What the AI Does (Behind the Scenes)

| Step | Module | What It Does |
|------|--------|--------------|
| **Classify** | `core/document_classifier.py` | Sends first page of cert PDF as image to GPT-4o Vision. Returns document type (COA/COCA/COC/Other) and confidence score. |
| **Extract Spec** | `core/spec_extractor.py` | Sends all pages of spec PDF to GPT-4o Vision. Extracts product name, material number, and all parameters with min/max limits and units. |
| **Extract Cert** | `core/cert_extractor.py` | Sends all pages of cert PDF to GPT-4o Vision. Extracts product name, batch number, dates, supplier, and all measured parameter values. Uses different prompts for COA vs COCA/COC. |
| **Compare** | `core/comparator.py` | Uses AI-powered parameter alignment to match spec params to cert params despite naming differences. Checks numeric values against limits. Handles unit normalization. Detects product mismatches. Returns PASS/FAIL/REVIEW per parameter. |

All AI calls use the model defined in `config.DEFAULT_MODEL` (currently `gpt-4o`) with temperature `0` for deterministic results.

---

## Supported Certificate Types

| Type | Full Name | What AI Looks For |
|------|-----------|-------------------|
| **COA** | Certificate of Analysis | Lab test results with measured values per parameter |
| **COCA** | Certificate of Compliance/Analysis | Compliance attestation, may include test data |
| **COC** | Certificate of Conformance | Statement-based — certifies product meets spec (may have no numeric data) |

The certificate type is **auto-detected** by the AI classifier — no manual selection needed.

---

## Expected Output Examples

### PASS Result
- All extracted cert parameters fall within spec limits
- Green banner, all metric cards show passes
- No critical issues or review items

### FAIL Result
- One or more parameters are outside spec limits
- Red banner with reason
- Critical Issues section lists each failure with spec vs cert values
- Parameters that passed are still shown in the table

### REVIEW Result
- Parameters could not be conclusively verified (naming mismatch, missing data, qualitative params)
- Amber banner
- Items for Review section lists each ambiguous parameter
- Common for COCA/COC certificates with compliance statements instead of numeric data

### Product Mismatch
- If spec and cert are for different products, the comparator detects this
- Returns immediate FAIL with "Product mismatch" reason
- No parameter comparison is performed

---

## Configuration

All config is centralized in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_MODEL` | `gpt-4o` | OpenAI model for all AI calls |
| `TEMPERATURE` | `0` | Deterministic output |
| `AUDIT_LOG` | `logs/audit_log.csv` | Path to audit log file |
| `JSON_OUTPUT_DIR` | `outputs/structured_json/` | Where extracted JSONs are saved |
| `IMAGE_DPI` | `200` | PDF rendering resolution |
| `MAX_PAGES_PER_DOC` | `10` | Max pages sent to Vision API |

---

## File Structure

```
intelligent_safety_net/
├── ui.py                          ← Main UI (this file)
├── ui_old.py                      ← Phase 0 backup (read-only audit viewer)
├── config.py                      ← Central configuration
├── model_switcher.py              ← Model selection utility
├── core/
│   ├── document_classifier.py     ← Step 1: AI classification
│   ├── spec_extractor.py          ← Step 2: Spec parameter extraction
│   ├── cert_extractor.py          ← Step 3: Cert data extraction
│   ├── comparator.py              ← Step 4: AI-powered comparison
│   ├── unit_normalizer.py         ← Unit conversion utilities
│   ├── pdf_renderer.py            ← PDF → image conversion
│   └── logger.py                  ← Audit logging
├── data/
│   ├── specs/                     ← Product specification PDFs
│   └── certificates/              ← Supplier certificate PDFs
├── logs/
│   └── audit_log.csv              ← Validation audit trail
└── outputs/
    └── structured_json/           ← Extracted JSON outputs
```

---

## Footer

A centered, muted footer at the bottom:

> *Intelligent Document Verification | Powered by GPT-4o Vision*
