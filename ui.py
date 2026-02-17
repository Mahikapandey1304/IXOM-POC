"""
Intelligent Safety Net — Demo UI
=================================
Full-featured Streamlit dashboard for IXOM product safety verification.

Features:
  1. Upload supplier certificate (PDF) → AI classifies & validates
  2. Select IXOM product spec or upload custom spec
  3. Side-by-side parameter comparison with traffic-light highlighting
  4. Wrong document detection (not a certificate)
  5. Value mismatch alerts with severity levels
  6. Batch audit log history
  7. Extracted data viewer

Run:  streamlit run ui.py
"""

import sys
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# ─── Ensure project root on path ─────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import config
from model_switcher import get_model
from core.document_classifier import classify_document
from core.spec_extractor import extract_spec
from core.cert_extractor import extract_certificate
from core.comparator import compare_documents
from core.unit_normalizer import normalize_param_name

# ─── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="IXOM Intelligent Safety Net",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #bbdefb; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    .status-pass {
        background-color: #28a745; color: white; padding: 6px 18px;
        border-radius: 20px; font-weight: bold; font-size: 1.1rem;
        display: inline-block;
    }
    .status-fail {
        background-color: #dc3545; color: white; padding: 6px 18px;
        border-radius: 20px; font-weight: bold; font-size: 1.1rem;
        display: inline-block;
    }
    .status-review {
        background-color: #ffc107; color: #333; padding: 6px 18px;
        border-radius: 20px; font-weight: bold; font-size: 1.1rem;
        display: inline-block;
    }
    .status-error {
        background-color: #dc3545; color: white; padding: 6px 18px;
        border-radius: 20px; font-weight: bold; font-size: 1.1rem;
        display: inline-block;
    }

    .alert-critical {
        background: #4a1a1a; border-left: 5px solid #ff6b6b;
        padding: 1rem; margin: 0.5rem 0; border-radius: 4px;
        color: #ffcdd2;
    }
    .alert-critical h4 { color: #ff8a80; }
    .alert-critical p { color: #ffcdd2; }
    .alert-critical strong { color: #ffffff; }

    .alert-warning {
        background: #3e3518; border-left: 5px solid #ffca28;
        padding: 1rem; margin: 0.5rem 0; border-radius: 4px;
        color: #fff8e1;
    }
    .alert-warning h4 { color: #ffd54f; }
    .alert-warning p { color: #fff8e1; }
    .alert-warning strong { color: #ffffff; }

    .alert-success {
        background: #1b3a1b; border-left: 5px solid #66bb6a;
        padding: 1rem; margin: 0.5rem 0; border-radius: 4px;
        color: #c8e6c9;
    }
    .alert-success h4 { color: #81c784; }
    .alert-success p { color: #c8e6c9; }
    .alert-success strong { color: #ffffff; }
</style>
""", unsafe_allow_html=True)


# ─── Constants ────────────────────────────────────────────────────────
AUDIT_LOG = config.AUDIT_LOG
JSON_DIR = config.JSON_OUTPUT_DIR
SOURCE_PDFS = config.SOURCE_PDFS_DIR

STATUS_BADGE = {
    "PASS": '<span class="status-pass">✅ PASS — Certificate Verified</span>',
    "FAIL": '<span class="status-fail">❌ FAIL — Certificate Rejected</span>',
    "REVIEW": '<span class="status-review">🔍 REVIEW — Manual Check Required</span>',
    "ERROR": '<span class="status-error">⚠️ ERROR — Processing Failed</span>',
}


def _save_uploaded_file(uploaded_file) -> str:
    """Save an uploaded file to a temp location and return the path."""
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getvalue())
    tmp.close()
    return tmp.name


def _get_spec_options() -> dict:
    """Get available IXOM spec PDFs from the mapping file."""
    specs = {}
    if config.MAPPING_FILE.exists():
        mapping = pd.read_excel(config.MAPPING_FILE)
        for _, row in mapping.iterrows():
            material = row.get("Material_Number", "")
            spec_file = row.get("Spec_File", "")
            industry = row.get("Industry", "")
            if spec_file and not pd.isna(spec_file):
                label = f"{material} — {spec_file} [{industry}]"
                specs[label] = str(spec_file)
    return specs


def _resolve_spec_path(filename: str) -> str:
    """Find the spec PDF in known locations."""
    for folder in [config.SPECS_DIR, SOURCE_PDFS, PROJECT_ROOT / "data"]:
        path = folder / filename
        if path.exists():
            return str(path)
    return None


def _color_param_row(row):
    """Apply row-level coloring based on status (dark-mode friendly)."""
    status = row.get("Status", "")
    if status == "FAIL":
        return ["background-color: #4a1a1a; color: #ff8a80"] * len(row)
    elif status == "REVIEW":
        return ["background-color: #3e3518; color: #ffd54f"] * len(row)
    elif status == "PASS":
        return ["background-color: #1b3a1b; color: #81c784"] * len(row)
    elif status == "NOT_IN_CERT":
        return ["background-color: #2a2a3a; color: #9e9e9e"] * len(row)
    return ["color: #e0e0e0"] * len(row)


# ═══════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
    <h1>🛡️ Intelligent Safety Net</h1>
    <p>IXOM Product Safety Verification Engine — Supplier Certificate Validation</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    model = st.selectbox(
        "AI Model",
        config.AVAILABLE_MODELS,
        index=0,
        help="GPT-4o is recommended for best accuracy"
    )
    st.markdown(f"**Temperature:** {config.TEMPERATURE}")
    st.markdown("---")

    st.markdown("### 📖 How It Works")
    st.markdown("""
    1. **Upload** a supplier certificate (PDF)
    2. **Select** the IXOM product spec to validate against
    3. **AI classifies** the document type instantly
    4. **Parameters extracted** from both documents
    5. **Comparison** checks every value against spec limits
    6. **Result** — Pass ✅ / Fail ❌ / Review 🔍
    """)
    st.markdown("---")

    st.markdown("### 🚨 What Gets Detected")
    st.markdown("""
    - ❌ **Wrong document** — supplier sends invoice instead of certificate
    - ❌ **Value out of range** — test result outside spec limits
    - 🔍 **Missing parameters** — certificate doesn't cover all spec items
    - 🔍 **Unit mismatches** — incompatible measurement units
    - ✅ **Full compliance** — all values within specification
    """)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN TABS
# ═══════════════════════════════════════════════════════════════════════
tab_validate, tab_batch, tab_history = st.tabs([
    "🔬 Validate Certificate",
    "📦 Batch Processing",
    "📊 Audit History"
])


# ─────────────────────────────────────────────────────────────────────
#  TAB 1: VALIDATE CERTIFICATE (Upload & Compare)
# ─────────────────────────────────────────────────────────────────────
with tab_validate:
    st.markdown("## Upload & Validate Supplier Certificate")
    st.markdown("Upload a supplier certificate and select the IXOM product specification to validate against.")

    col_spec, col_cert = st.columns(2)

    # ── LEFT: IXOM Product Specification ──
    with col_spec:
        st.markdown("### 📋 IXOM Product Specification")
        spec_source = st.radio(
            "Specification source:",
            ["Select from IXOM catalog", "Upload custom spec PDF"],
            horizontal=True,
            key="spec_source",
        )

        spec_path = None

        if spec_source == "Select from IXOM catalog":
            spec_options = _get_spec_options()
            if spec_options:
                selected_spec = st.selectbox(
                    "Select product specification:",
                    list(spec_options.keys()),
                    key="spec_select",
                )
                spec_filename = spec_options[selected_spec]
                spec_path = _resolve_spec_path(spec_filename)
                if spec_path:
                    st.success(f"📄 Loaded: **{spec_filename}**")
                else:
                    st.error(f"Spec file not found: {spec_filename}")
            else:
                st.warning("No mapping file found. Run `python build_mapping.py` first.")
        else:
            spec_upload = st.file_uploader(
                "Upload Product Specification PDF",
                type=["pdf"],
                key="spec_upload",
            )
            if spec_upload:
                spec_path = _save_uploaded_file(spec_upload)
                st.success(f"📄 Uploaded: **{spec_upload.name}**")

    # ── RIGHT: Supplier Certificate ──
    with col_cert:
        st.markdown("### 📜 Supplier Certificate")
        cert_type_select = st.selectbox(
            "Expected certificate type:",
            ["COA (Certificate of Analysis)", "COCA (Certificate of Compliance/Analysis)", "COC (Certificate of Conformance)"],
            key="cert_type",
        )
        cert_type = cert_type_select.split(" ")[0]

        cert_upload = st.file_uploader(
            "Upload Supplier Certificate PDF",
            type=["pdf"],
            key="cert_upload",
            help="Drag & drop or browse for the supplier's certificate document"
        )

        cert_path = None
        if cert_upload:
            cert_path = _save_uploaded_file(cert_upload)
            st.success(f"📜 Uploaded: **{cert_upload.name}**")

    # ── VALIDATE BUTTON ──
    st.markdown("---")

    if spec_path and cert_path:
        if st.button("🚀 Validate Certificate", type="primary", use_container_width=True):

            progress_bar = st.progress(0, text="Starting validation...")
            results_container = st.container()

            with results_container:
                try:
                    # ── Step 1: Classify ──
                    progress_bar.progress(10, text="Step 1/4 — Classifying document...")
                    classification = classify_document(cert_path, model)
                    detected_type = classification.get("document_type", "Unknown")
                    confidence = classification.get("confidence_score", 0.0)

                    # ── WRONG DOCUMENT ALERT ──
                    valid_cert_types = ["COA", "COCA", "COC", "Product_Specification"]
                    is_wrong_doc = detected_type not in valid_cert_types

                    if is_wrong_doc:
                        progress_bar.progress(100, text="⚠️ Wrong document detected!")
                        st.markdown(STATUS_BADGE.get("FAIL", ""), unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="alert-critical">
                            <h4>🚨 WRONG DOCUMENT DETECTED</h4>
                            <p>The uploaded file is <strong>NOT a valid certificate</strong>.</p>
                            <p><strong>Detected as:</strong> {detected_type} (confidence: {confidence:.0%})</p>
                            <p><strong>Expected:</strong> {cert_type}</p>
                            <p>The supplier may have sent the wrong file (e.g., an invoice, a product brochure, 
                            or an unrelated document). This document should be <strong>rejected immediately</strong> 
                            and the correct certificate requested from the supplier.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"**AI Reasoning:** {classification.get('reasoning', 'N/A')}")
                        st.stop()

                    # Show classification result
                    st.markdown("#### 📄 Document Classification")
                    cls_col1, cls_col2, cls_col3 = st.columns(3)
                    cls_col1.metric("Detected Type", detected_type)
                    cls_col2.metric("Confidence", f"{confidence:.0%}")
                    cls_col3.metric("Product", classification.get("product_name", "—")[:30])

                    if detected_type != cert_type and detected_type != "Product_Specification":
                        st.warning(f"⚠️ Document detected as **{detected_type}** but you selected **{cert_type}**. Proceeding with detected type.")
                        cert_type = detected_type

                    # ── Step 2: Extract Spec ──
                    progress_bar.progress(30, text="Step 2/4 — Extracting specification parameters...")
                    spec_data = extract_spec(spec_path, model)
                    n_spec = len(spec_data.get("parameters", []))

                    # ── Step 3: Extract Certificate ──
                    progress_bar.progress(55, text="Step 3/4 — Extracting certificate data...")
                    cert_data = extract_certificate(cert_path, model, expected_type=cert_type)
                    n_cert = len(cert_data.get("parameters", []))

                    # ── Step 4: Compare (AI-powered alignment) ──
                    progress_bar.progress(80, text="Step 4/4 — AI-powered parameter alignment & comparison...")
                    comparison = compare_documents(spec_data, cert_data, cert_type=cert_type, model=model)

                    progress_bar.progress(100, text="✅ Validation complete!")
                    time.sleep(0.5)
                    progress_bar.empty()

                    # ═══════════════════════════════════════════════════
                    #  RESULTS
                    # ═══════════════════════════════════════════════════
                    st.markdown("---")

                    # ── Overall Status Badge ──
                    status = comparison.get("status", "ERROR")
                    st.markdown(STATUS_BADGE.get(status, ""), unsafe_allow_html=True)

                    # ── PRODUCT MISMATCH ALERT ──
                    if comparison.get("product_mismatch"):
                        cert_prod = comparison.get("cert_product_name", "Unknown")
                        spec_prod = comparison.get("product_name", "Unknown")
                        st.markdown(f"""
                        <div class="alert-critical">
                            <h4>🚨 PRODUCT MISMATCH DETECTED</h4>
                            <p>The uploaded certificate is for a <strong>DIFFERENT PRODUCT</strong> than the selected specification.</p>
                            <p><strong>Specification product:</strong> {spec_prod}</p>
                            <p><strong>Certificate product:</strong> {cert_prod}</p>
                            <p>This certificate <strong>cannot be used</strong> to validate this product specification.
                            Please upload the correct certificate that matches the product.</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # ── Summary Metrics ──
                    st.markdown("#### 📊 Validation Summary")
                    m1, m2, m3, m4, m5, m6 = st.columns(6)
                    m1.metric("Parameters Checked", comparison.get("parameters_checked", 0))
                    m2.metric("✅ Passed", comparison.get("parameters_passed", 0))
                    m3.metric("❌ Failed", comparison.get("parameters_failed", 0))
                    m4.metric("🔍 Review", comparison.get("parameters_review", 0))
                    m5.metric("➖ Not in Cert", comparison.get("parameters_not_in_cert", 0))
                    m6.metric("Batch No.", comparison.get("batch_number", "—") or "—")

                    # ── Reason ──
                    reason = comparison.get("reason", "")
                    if status == "FAIL":
                        st.markdown(f"""
                        <div class="alert-critical">
                            <h4>❌ Certificate REJECTED — Values Outside Specification</h4>
                            <p>{reason}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    elif status == "REVIEW":
                        st.markdown(f"""
                        <div class="alert-warning">
                            <h4>🔍 Manual Review Required</h4>
                            <p>{reason}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="alert-success">
                            <h4>✅ Certificate Verified — All Parameters Within Specification</h4>
                            <p>{reason}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # ── Compliance Statement (COCA/COC) ──
                    comp_statement = comparison.get("compliance_statement", "")
                    if comp_statement:
                        st.markdown(f"""
                        <div class="alert-success">
                            <h4>📜 Compliance Statement</h4>
                            <p>{comp_statement}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # ── Parameter-by-Parameter Comparison Table ──
                    details = comparison.get("details", [])
                    if details:
                        st.markdown("#### ⚖️ Parameter-by-Parameter Comparison")

                        param_rows = []
                        for d in details:
                            icon = {"PASS": "✅", "FAIL": "❌", "REVIEW": "🔍", "NOT_IN_CERT": "➖"}.get(d.get("status", ""), "")
                            cert_param_name = d.get("cert_parameter", "")
                            param_rows.append({
                                "Status": d.get("status", ""),
                                " ": icon,
                                "Spec Parameter": d.get("parameter", ""),
                                "Matched Cert Parameter": cert_param_name if cert_param_name else "— not found —",
                                "Spec Min": d.get("spec_min", ""),
                                "Spec Max": d.get("spec_max", ""),
                                "Certificate Value": d.get("cert_value", ""),
                                "Unit": d.get("cert_unit", "") or d.get("spec_unit", ""),
                                "Verdict": d.get("reason", "—") or "Within spec",
                            })

                        param_df = pd.DataFrame(param_rows)
                        styled_params = param_df.style.apply(_color_param_row, axis=1)
                        st.dataframe(styled_params, use_container_width=True, height=min(450, 60 + len(param_rows) * 38))

                        # Count issues
                        fails = [d for d in details if d.get("status") == "FAIL"]
                        reviews = [d for d in details if d.get("status") == "REVIEW"]
                        not_in_cert = [d for d in details if d.get("status") == "NOT_IN_CERT"]

                        if fails:
                            st.markdown("#### 🚨 Critical Issues — Values Outside Specification")
                            for f in fails:
                                st.error(f"**{f['parameter']}**: {f['reason']}")

                        if reviews:
                            st.markdown("#### ⚠️ Items Requiring Review")
                            for r in reviews:
                                st.warning(f"**{r['parameter']}**: {r['reason']}")

                        if not_in_cert:
                            st.markdown("#### ➖ Parameters Not Found in Certificate")
                            st.info("These spec parameters are not tested in the certificate (e.g., visual inspection items). They require separate verification.")
                            for n in not_in_cert:
                                st.caption(f"• {n['parameter']}: {n.get('reason', 'Not found in certificate')}")

                    # ── Side-by-Side Extracted Data ──
                    st.markdown("---")
                    with st.expander("📋 View Full Extracted Data (JSON)", expanded=False):
                        json_col1, json_col2 = st.columns(2)
                        with json_col1:
                            st.markdown("**Specification Data**")
                            st.json(spec_data)
                        with json_col2:
                            st.markdown("**Certificate Data**")
                            st.json(cert_data)

                except Exception as e:
                    progress_bar.empty()
                    st.markdown(STATUS_BADGE.get("ERROR", ""), unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="alert-critical">
                        <h4>⚠️ Processing Error</h4>
                        <p><strong>{type(e).__name__}:</strong> {str(e)}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.exception(e)
    else:
        st.info("👆 Upload both a **Product Specification** and a **Supplier Certificate** above, then click **Validate Certificate**.")


# ─────────────────────────────────────────────────────────────────────
#  TAB 2: BATCH PROCESSING
# ─────────────────────────────────────────────────────────────────────
with tab_batch:
    st.markdown("## 📦 Batch Processing")
    st.markdown("Process all mapped product-certificate pairs from the IXOM catalog at once.")

    if config.MAPPING_FILE.exists():
        mapping = pd.read_excel(config.MAPPING_FILE)
        st.markdown(f"**{len(mapping)} products** configured in mapping file")

        display_mapping = mapping[["SN", "Industry", "Material_Number", "Spec_File", "COA_File", "COCA_File", "COC_File"]].copy()
        display_mapping = display_mapping.fillna("—")
        st.dataframe(display_mapping, use_container_width=True, height=400)

        batch_col1, batch_col2 = st.columns(2)
        with batch_col1:
            batch_model = st.selectbox("Model for batch", config.AVAILABLE_MODELS, key="batch_model")
        with batch_col2:
            batch_mode = st.radio("Processing mode", ["Golden Test (3 pairs)", "Full Batch (all)"], horizontal=True)

        if st.button("🚀 Run Batch Processing", type="primary"):
            st.warning("⏳ For reliability, batch processing runs via the terminal:")
            if batch_mode.startswith("Golden"):
                st.code(f"cd {PROJECT_ROOT}\npython main.py --golden-test --model {batch_model}", language="bash")
            else:
                st.code(f"cd {PROJECT_ROOT}\npython main.py --model {batch_model}", language="bash")
            st.info("After the batch completes, switch to the **Audit History** tab to view all results.")
    else:
        st.warning("Mapping file not found. Run `python build_mapping.py` first.")


# ─────────────────────────────────────────────────────────────────────
#  TAB 3: AUDIT HISTORY
# ─────────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("## 📊 Audit Log History")

    if AUDIT_LOG.exists():
        log = pd.read_csv(AUDIT_LOG)

        if not log.empty:
            total = len(log)
            passed = len(log[log["Status"] == "PASS"])
            failed = len(log[log["Status"] == "FAIL"])
            review = len(log[log["Status"] == "REVIEW"])
            errors = len(log[log["Status"] == "ERROR"])

            h1, h2, h3, h4, h5 = st.columns(5)
            h1.metric("Total Processed", total)
            h2.metric("✅ Passed", passed, delta=f"{passed/total*100:.0f}%" if total else "0%")
            h3.metric("❌ Failed", failed)
            h4.metric("🔍 Review", review)
            h5.metric("⚠️ Errors", errors)

            st.markdown("---")
            f1, f2, f3 = st.columns(3)
            with f1:
                hist_status = st.selectbox("Filter Status", ["ALL"] + sorted(log["Status"].dropna().unique().tolist()), key="hist_status")
            with f2:
                cert_opts = ["ALL"]
                if "Cert_Type" in log.columns:
                    cert_opts += sorted(log["Cert_Type"].dropna().unique().tolist())
                hist_cert = st.selectbox("Filter Cert Type", cert_opts, key="hist_cert")
            with f3:
                model_opts = ["ALL"]
                if "Model" in log.columns:
                    model_opts += sorted(log["Model"].dropna().unique().tolist())
                hist_model = st.selectbox("Filter Model", model_opts, key="hist_model")

            filtered = log.copy()
            if hist_status != "ALL":
                filtered = filtered[filtered["Status"] == hist_status]
            if hist_cert != "ALL":
                filtered = filtered[filtered["Cert_Type"] == hist_cert]
            if hist_model != "ALL":
                filtered = filtered[filtered["Model"] == hist_model]

            display_cols = [c for c in [
                "Timestamp", "Spec_File", "Cert_File", "Cert_Type", "Status",
                "Product_Name", "Material_Number", "Batch_Number", "Confidence",
                "Parameters_Checked", "Parameters_Passed", "Parameters_Failed",
                "Parameters_Missing", "Reason",
            ] if c in filtered.columns]

            def _hist_color(val):
                color_map = {
                    "PASS": ("#1b3a1b", "#81c784"),
                    "FAIL": ("#4a1a1a", "#ff8a80"),
                    "REVIEW": ("#3e3518", "#ffd54f"),
                    "ERROR": ("#3a1a1a", "#ff6b6b"),
                }
                pair = color_map.get(val)
                return f"background-color: {pair[0]}; color: {pair[1]}; font-weight: bold;" if pair else ""

            styled = filtered[display_cols].style.map(_hist_color, subset=["Status"] if "Status" in display_cols else [])
            st.dataframe(styled, use_container_width=True, height=400)
            st.caption(f"Showing {len(filtered)} of {total} records")

            st.markdown("---")
            st.markdown("#### 🔍 Inspect Result")
            if not filtered.empty:
                options = []
                for idx, row in filtered.iterrows():
                    icon = {"PASS": "✅", "FAIL": "❌", "REVIEW": "🔍", "ERROR": "⚠️"}.get(row.get("Status", ""), "")
                    options.append(f"{icon} {row.get('Spec_File', '')} ↔ {row.get('Cert_File', '')} ({row.get('Cert_Type', '')})")

                selected = st.selectbox("Select a record:", options, key="hist_select")
                sel_idx = options.index(selected)
                sel_row = filtered.iloc[sel_idx]

                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("**Specification Extracted Data**")
                    spec_stem = Path(str(sel_row.get("Spec_File", ""))).stem
                    spec_json = JSON_DIR / f"{spec_stem}_spec.json"
                    if spec_json.exists():
                        with open(spec_json) as f:
                            st.json(json.load(f))
                    else:
                        st.info("No extracted JSON available")

                with d2:
                    st.markdown("**Certificate Extracted Data**")
                    cert_stem = Path(str(sel_row.get("Cert_File", ""))).stem
                    ct = str(sel_row.get("Cert_Type", "coa")).lower()
                    cert_json = JSON_DIR / f"{cert_stem}_{ct}.json"
                    if cert_json.exists():
                        with open(cert_json) as f:
                            st.json(json.load(f))
                    else:
                        st.info("No extracted JSON available")

                st.markdown(f"""
                **Status:** {sel_row.get('Status', '')} | **Reason:** {sel_row.get('Reason', 'N/A')} |
                **Model:** {sel_row.get('Model', '')} | **Confidence:** {sel_row.get('Confidence', '')}
                """)
        else:
            st.info("Audit log is empty. Run a validation first.")
    else:
        st.info("No audit log yet. Validate a certificate or run a batch to create one.")


# ═══════════════════════════════════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #aaa; font-size: 0.85rem;">
    Intelligent Safety Net v0.1 — Phase 0 PoC | IXOM Product Safety Verification<br>
    Powered by GPT-4o Vision | Built with Streamlit
</div>
""", unsafe_allow_html=True)
