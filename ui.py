"""
Intelligent Document Verification — Demo UI
=============================================
Polished Streamlit dashboard for automated supplier certificate validation.

Run:  streamlit run ui.py
"""

import sys
import os
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from core.document_classifier import classify_document
from core.spec_extractor import extract_spec
from core.cert_extractor import extract_certificate
from core.comparator import compare_documents
from core.logger import log_result

# ── Config ──────────────────────────────────────────────────────────────
MODEL = config.DEFAULT_MODEL

# ── Page Setup ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Intelligent Document Verification",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Hide sidebar, hamburger, footer */
[data-testid="stSidebar"] {display:none}
#MainMenu {visibility:hidden}
footer {visibility:hidden}
header {visibility:hidden}

/* Global */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 1200px;
}

/* Hero header */
.hero-header {
    background: linear-gradient(135deg, #0a1628 0%, #1a3a5c 50%, #2a5a8c 100%);
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.2rem;
    border: 1px solid rgba(255,255,255,0.08);
}
.hero-header h1 {
    color: #ffffff;
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
    letter-spacing: 1.5px;
}
.hero-subtitle {
    color: #94a3b8;
    font-size: 0.85rem;
    margin: 0 0 0.8rem 0;
}
.pipeline-steps {
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
}
.pipeline-step {
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    border-radius: 20px;
    padding: 0.25rem 0.8rem;
    color: #93c5fd;
    font-size: 0.75rem;
    font-weight: 500;
}
.step-num {
    background: #3b82f6;
    color: white;
    border-radius: 50%;
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    margin-right: 0.3rem;
}

/* Upload section labels */
.upload-label {
    color: #e2e8f0;
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 0.4rem 0;
    padding: 0;
}

/* Kill ALL default spacing inside upload columns */
div[data-testid="stFileUploader"] {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}
div[data-testid="stFileUploader"] > section {
    padding: 0 !important;
}
div[data-testid="stFileUploader"] label {
    display: none !important;
}
.file-loaded {
    margin-top: 0.35rem !important;
    margin-bottom: 0 !important;
}

/* Tighten all vertical blocks globally */
div[data-testid="stVerticalBlock"] > div {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
.element-container {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* Status badges */
.status-pass {
    background: linear-gradient(135deg, #065f46, #047857);
    color: #6ee7b7;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.8rem;
}
.status-fail {
    background: linear-gradient(135deg, #7f1d1d, #991b1b);
    color: #fca5a5;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.8rem;
}
.status-review {
    background: linear-gradient(135deg, #78350f, #92400e);
    color: #fcd34d;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.8rem;
}

/* Alert panels */
.alert-success {
    background: rgba(6,78,59,0.3);
    border-left: 4px solid #10b981;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    color: #a7f3d0;
    font-size: 0.85rem;
}
.alert-error {
    background: rgba(127,29,29,0.3);
    border-left: 4px solid #ef4444;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    color: #fecaca;
    font-size: 0.85rem;
}
.alert-warning {
    background: rgba(120,53,15,0.3);
    border-left: 4px solid #f59e0b;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    color: #fde68a;
    font-size: 0.85rem;
}
.alert-info {
    background: rgba(30,58,138,0.3);
    border-left: 4px solid #3b82f6;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    color: #bfdbfe;
    font-size: 0.85rem;
}

/* Metric cards */
.metric-card {
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    text-align: center;
}
.metric-card .label {
    color: #94a3b8;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.3rem;
}
.metric-card .value {
    color: #f1f5f9;
    font-size: 1.5rem;
    font-weight: 700;
}

/* Section headers */
.section-header {
    color: #e2e8f0;
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid rgba(59,130,246,0.3);
}

/* Validate button */
.stButton > button {
    background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1e3a8a, #2563eb) !important;
    box-shadow: 0 4px 15px rgba(59,130,246,0.3) !important;
    transform: translateY(-1px) !important;
}

/* Reduce gaps globally */
.stRadio > div {
    gap: 0.3rem !important;
}
div[data-testid="stVerticalBlock"] > div {
    gap: 0.15rem !important;
}
div[data-testid="column"] > div {
    gap: 0.15rem !important;
}

/* Tighter spacing after tabs header */
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 0.5rem !important;
}

/* Table styling */
.comparison-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    margin-top: 0.5rem;
}
.comparison-table th {
    background: rgba(30,58,138,0.4);
    color: #93c5fd;
    padding: 0.5rem 0.6rem;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid rgba(59,130,246,0.3);
}
.comparison-table td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    color: #e2e8f0;
}
.comparison-table tr:hover {
    background: rgba(59,130,246,0.05);
}

/* Loaded/uploaded file confirmations */
.file-loaded {
    background: rgba(6,78,59,0.4);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 6px;
    padding: 0.3rem 0.8rem;
    color: #6ee7b7;
    font-size: 0.82rem;
    margin-top: 0.3rem !important;
    margin-bottom: 0 !important;
    line-height: 1.3;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}
.stTabs [data-baseweb="tab"] {
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
}

/* Getting started box */
.getting-started {
    background: rgba(30,58,138,0.15);
    border: 1px dashed rgba(59,130,246,0.3);
    border-radius: 10px;
    padding: 1.5rem 2rem;
    text-align: center;
    margin: 1rem 0;
}
.getting-started h4 {
    color: #93c5fd;
    margin: 0 0 0.5rem 0;
}
.getting-started p {
    color: #64748b;
    font-size: 0.85rem;
    margin: 0;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Helper functions ────────────────────────────────────────────────────
def status_badge(status: str) -> str:
    s = status.upper()
    cls = {"PASS": "status-pass", "FAIL": "status-fail"}.get(s, "status-review")
    return f'<span class="{cls}">{s}</span>'


def save_upload(uploaded_file) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


# ── Hero Header ─────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero-header">
    <h1>INTELLIGENT DOCUMENT VERIFICATION</h1>
    <p class="hero-subtitle">Automated Supplier Certificate Validation Engine</p>
    <div class="pipeline-steps">
        <span class="pipeline-step"><span class="step-num">1</span> Upload Documents</span>
        <span class="pipeline-step"><span class="step-num">2</span> AI Classification</span>
        <span class="pipeline-step"><span class="step-num">3</span> Parameter Extraction</span>
        <span class="pipeline-step"><span class="step-num">4</span> Compliance Check</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Tabs ────────────────────────────────────────────────────────────────
tab_validate, tab_history = st.tabs(["Validate Certificate", "Audit History"])

# =====================================================================
# TAB 1 — VALIDATE
# =====================================================================
with tab_validate:

    col_spec, col_cert = st.columns(2, gap="medium")

    # ── Left: Product Specification Upload ──
    with col_spec:
        st.markdown('<p class="upload-label">Product Specification</p>', unsafe_allow_html=True)
        spec_file = st.file_uploader(
            "Upload spec", type=["pdf"], key="spec_upload", label_visibility="collapsed",
        )
        spec_path = None
        if spec_file:
            spec_path = save_upload(spec_file)
            st.markdown(f'<div class="file-loaded">Loaded: {spec_file.name}</div>', unsafe_allow_html=True)

    # ── Right: Supplier Certificate Upload ──
    with col_cert:
        st.markdown('<p class="upload-label">Supplier Certificate</p>', unsafe_allow_html=True)
        cert_file = st.file_uploader(
            "Upload cert", type=["pdf"], key="cert_upload", label_visibility="collapsed",
        )
        cert_path = None
        if cert_file:
            cert_path = save_upload(cert_file)
            st.markdown(f'<div class="file-loaded">Uploaded: {cert_file.name}</div>', unsafe_allow_html=True)

    # ── Validate Button ─────────────────────────────────────────────
    if not (spec_path and cert_path):
        st.markdown(
            """
        <div class="getting-started">
            <h4>Getting Started</h4>
            <p>Upload a product specification and a supplier certificate to begin validation.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        if st.button("Validate Certificate", use_container_width=True):

            # ── Progress pipeline ──
            progress_bar = st.progress(0, text="Classifying document...")
            t0 = time.time()

            # 1/4 — Classify
            classification = classify_document(cert_path, MODEL)
            detected_type = classification.get("document_type", "COA").upper()
            valid_types = ["COA", "COCA", "COC"]
            cert_type = detected_type if detected_type in valid_types else "COA"
            confidence = classification.get("confidence_score", 0)
            progress_bar.progress(25, text="Extracting specification parameters...")

            # 2/4 — Extract spec
            spec_data = extract_spec(spec_path, MODEL)
            product = spec_data.get("product_name", "Unknown")
            spec_params = spec_data.get("parameters", [])
            progress_bar.progress(50, text="Extracting certificate data...")

            # 3/4 — Extract certificate
            cert_data = extract_certificate(cert_path, MODEL, expected_type=cert_type)
            cert_product = cert_data.get("product_name", "Unknown")
            cert_params = cert_data.get("parameters", [])
            progress_bar.progress(75, text="Running compliance check...")

            # 4/4 — Compare
            result = compare_documents(spec_data, cert_data, cert_type=cert_type, model=MODEL)
            progress_bar.progress(100, text="Complete!")
            elapsed = time.time() - t0

            # Clear progress bar
            time.sleep(0.3)
            progress_bar.empty()

            # ── FINAL REPORT ──────────────────────────────────────
            # Read correct keys from comparator output
            overall = result.get("status", "REVIEW").upper()
            details = result.get("details", [])
            reason = result.get("reason", "")

            n_pass = result.get("parameters_passed", 0)
            n_fail = result.get("parameters_failed", 0)
            n_review = result.get("parameters_review", 0)
            n_not_in_cert = result.get("parameters_not_in_cert", 0)

            # Also count from details as fallback
            if not (n_pass or n_fail or n_review) and details:
                n_pass = sum(1 for d in details if d.get("status", "").upper() == "PASS")
                n_fail = sum(1 for d in details if d.get("status", "").upper() == "FAIL")
                n_review = sum(1 for d in details if d.get("status", "").upper() == "REVIEW")
                n_not_in_cert = sum(1 for d in details if d.get("status", "").upper() == "NOT_IN_CERT")

            # Overall result banner
            banner_cls = {
                "PASS": "alert-success",
                "FAIL": "alert-error",
            }.get(overall, "alert-warning")
            st.markdown(
                f'<div class="{banner_cls}" style="text-align:center;font-size:1.1rem;padding:1rem;">'
                f"<strong>Overall Result: {overall}</strong> &nbsp;|&nbsp; "
                f"{cert_type} &nbsp;|&nbsp; "
                f"Confidence: {confidence:.0%} &nbsp;|&nbsp; "
                f"Time: {elapsed:.1f}s"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Summary line
            st.markdown(
                f'<div class="alert-info" style="margin-top:0.5rem;">'
                f"<strong>Product:</strong> {product} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<strong>Certificate:</strong> {cert_product} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<strong>Spec params:</strong> {len(spec_params)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<strong>Cert params:</strong> {len(cert_params)}"
                f"</div>",
                unsafe_allow_html=True,
            )

            if reason:
                st.markdown(
                    f'<div class="alert-warning" style="margin-top:0.3rem;"><strong>Reason:</strong> {reason}</div>',
                    unsafe_allow_html=True,
                )

            # Metric cards
            m1, m2, m3, m4 = st.columns(4)
            for col, label, val in [
                (m1, "PASSED", n_pass),
                (m2, "FAILED", n_fail),
                (m3, "REVIEW", n_review),
                (m4, "NOT IN CERT", n_not_in_cert),
            ]:
                col.markdown(
                    f'<div class="metric-card"><div class="label">{label}</div><div class="value">{val}</div></div>',
                    unsafe_allow_html=True,
                )

            # Parameter details table
            if details:
                st.markdown('<div class="section-header">Parameter Details</div>', unsafe_allow_html=True)
                rows = ""
                for d in details:
                    s = d.get("status", "REVIEW").upper()
                    badge = status_badge(s)
                    param = d.get("parameter", "") or d.get("spec_parameter", "—")
                    # Build spec range from min/max
                    s_min = d.get("spec_min", "")
                    s_max = d.get("spec_max", "")
                    if s_min and s_max:
                        spec_range = f"{s_min} – {s_max}"
                    elif s_min:
                        spec_range = f"Min {s_min}"
                    elif s_max:
                        spec_range = f"Max {s_max}"
                    else:
                        spec_range = "—"
                    spec_val = d.get("spec_value", "—") or "—"
                    cert_val = d.get("cert_value", "—") or "—"
                    comment = d.get("reason", "") or ""
                    rows += f"<tr><td>{badge}</td><td>{param}</td><td>{spec_range}</td><td>{spec_val}</td><td>{cert_val}</td><td>{comment}</td></tr>"

                st.markdown(
                    f"""
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Parameter</th>
                            <th>Spec Range</th>
                            <th>Spec Value</th>
                            <th>Cert Value</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                """,
                    unsafe_allow_html=True,
                )

            # Critical failures
            critical = [d for d in details if d.get("status", "").upper() == "FAIL"]
            if critical:
                st.markdown('<div class="section-header">Critical Issues</div>', unsafe_allow_html=True)
                for d in critical:
                    st.markdown(
                        f'<div class="alert-error"><strong>{d.get("parameter","—")}:</strong> '
                        f'Spec={d.get("spec_value","—")} vs Cert={d.get("cert_value","—")} — '
                        f'{d.get("reason","")}</div>',
                        unsafe_allow_html=True,
                    )

            # Items for review
            reviews = [d for d in details if d.get("status", "").upper() == "REVIEW"]
            if reviews:
                st.markdown('<div class="section-header">Items for Review</div>', unsafe_allow_html=True)
                for d in reviews:
                    st.markdown(
                        f'<div class="alert-warning"><strong>{d.get("parameter","—")}:</strong> '
                        f'{d.get("reason","")}</div>',
                        unsafe_allow_html=True,
                    )

            # Log result
            try:
                log_result(
                    spec_file=spec_file.name if spec_file else "custom",
                    cert_file=cert_file.name if cert_file else "unknown",
                    cert_type=cert_type,
                    model=MODEL,
                    classification=classification,
                    comparison=result,
                )
            except Exception:
                pass

# =====================================================================
# TAB 2 — AUDIT HISTORY
# =====================================================================
with tab_history:
    st.markdown('<div class="section-header">Audit History</div>', unsafe_allow_html=True)

    log_path = str(config.AUDIT_LOG)
    if not os.path.exists(log_path):
        st.markdown(
            '<div class="alert-info">No audit records yet. Validate a certificate to create the first entry.</div>',
            unsafe_allow_html=True,
        )
    else:
        import pandas as pd

        df = pd.read_csv(log_path)

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            statuses = ["ALL"] + sorted(df["Status"].dropna().unique().tolist()) if "Status" in df.columns else ["ALL"]
            sel_status = st.selectbox("Filter by Status", statuses)
        with col_f2:
            cert_types = ["ALL"] + sorted(df["Cert_Type"].dropna().unique().tolist()) if "Cert_Type" in df.columns else ["ALL"]
            sel_cert = st.selectbox("Filter by Cert Type", cert_types)

        filtered = df.copy()
        if sel_status != "ALL" and "Status" in filtered.columns:
            filtered = filtered[filtered["Status"] == sel_status]
        if sel_cert != "ALL" and "Cert_Type" in filtered.columns:
            filtered = filtered[filtered["Cert_Type"] == sel_cert]

        # Drop Model column if present
        if "Model" in filtered.columns:
            filtered = filtered.drop(columns=["Model"])

        # Metrics
        total = len(filtered)
        n_p = len(filtered[filtered["Status"] == "PASS"]) if "Status" in filtered.columns else 0
        n_f = len(filtered[filtered["Status"] == "FAIL"]) if "Status" in filtered.columns else 0
        n_r = len(filtered[filtered["Status"] == "REVIEW"]) if "Status" in filtered.columns else 0

        mc1, mc2, mc3, mc4 = st.columns(4)
        for col, lbl, v in [(mc1, "TOTAL", total), (mc2, "PASSED", n_p), (mc3, "FAILED", n_f), (mc4, "REVIEW", n_r)]:
            col.markdown(
                f'<div class="metric-card"><div class="label">{lbl}</div><div class="value">{v}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"<br><small>Showing {len(filtered)} of {len(df)} records</small>", unsafe_allow_html=True)
        st.dataframe(filtered, use_container_width=True, hide_index=True)

# ── Footer ──────────────────────────────────────────────────────────────
st.markdown(
    """
<div style="text-align:center; color:#475569; font-size:0.7rem; margin-top:2rem; padding-top:0.8rem; border-top:1px solid rgba(255,255,255,0.05);">
    Intelligent Document Verification | Powered by GPT-4o Vision
</div>
""",
    unsafe_allow_html=True,
)
