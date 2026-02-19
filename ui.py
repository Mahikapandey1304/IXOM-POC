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
import base64
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

# ── IXOM Logo ────────────────────────────────────────────────────────────
_logo_path = Path(__file__).parent / "assets" / "ixom_logo.png"
if _logo_path.exists():
    _logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode()
    _logo_src = f"data:image/png;base64,{_logo_b64}"
else:
    _logo_src = ""

# ── CSS — IXOM Light Theme ──────────────────────────────────────────────
st.markdown(
    f"""
<style>
/* ── Hide Streamlit chrome ── */
[data-testid="stSidebar"] {{display:none}}
#MainMenu {{visibility:hidden}}
footer {{visibility:hidden}}
header {{visibility:hidden}}

/* ── Global ── */
.stApp {{
    background-color: #edf1f5 !important;
}}
.block-container {{
    padding-top: 0 !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
}}

/* ══════════════════════════════════════
   HERO HEADER
   ══════════════════════════════════════ */
.hero-wrap {{
    background: #ffffff;
    margin: 0 -3rem 0 -3rem;
    padding: 2rem 3rem 1.8rem 3rem;
    border-bottom: 1px solid #e0e4e8;
    margin-bottom: 1.5rem;
}}
.hero-wrap img.ixom-logo {{
    height: 58px;
    margin-bottom: 1rem;
    display: block;
}}
.hero-wrap h1 {{
    color: #1a1a2e;
    font-size: 2.3rem;
    font-weight: 700;
    margin: 0 0 0.25rem 0;
    line-height: 1.15;
}}
.hero-wrap .subtitle {{
    color: #7a8a9a;
    font-size: 1.05rem;
    font-weight: 400;
    margin: 0;
}}

/* ══════════════════════════════════════
   UPLOAD CARDS — st.container(border=True)
   ══════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: #ffffff !important;
    border: 1px solid #d5dbe2 !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
    padding: 0 !important;
    overflow: visible !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    padding: 1.4rem 1.6rem !important;
}}

/* Upload card title */
.upload-title {{
    color: #1a1a2e;
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    padding: 0;
}}

/* ══════════════════════════════════════
   FILE UPLOADER restyle
   ══════════════════════════════════════ */
/* Hide default label */
div[data-testid="stFileUploader"] label {{
    display: none !important;
}}
div[data-testid="stFileUploader"] {{
    margin: 0 !important;
}}
div[data-testid="stFileUploader"] section {{
    padding: 0 !important;
}}

/* ── DROPZONE: tall, centered, dashed border ── */
div[data-testid="stFileUploaderDropzone"] {{
    background: #fafbfc !important;
    border: 2.5px dashed #c0c8d0 !important;
    border-radius: 14px !important;
    padding: 2.5rem 1.5rem !important;
    min-height: 230px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.3rem !important;
    transition: border-color 0.25s, background 0.25s !important;
    cursor: pointer !important;
}}
div[data-testid="stFileUploaderDropzone"]:hover {{
    border-color: #00838f !important;
    background: #f2fafa !important;
}}

/* Cloud icon → teal, large */
div[data-testid="stFileUploaderDropzone"] svg {{
    color: #00838f !important;
    fill: #00838f !important;
    width: 56px !important;
    height: 56px !important;
    margin-bottom: 0.5rem !important;
    opacity: 0.85;
}}

/* Text inside dropzone */
div[data-testid="stFileUploaderDropzone"] span {{
    color: #3a4a5a !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
}}
div[data-testid="stFileUploaderDropzone"] small {{
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
}}

/* Browse files button → teal pill */
div[data-testid="stFileUploaderDropzone"] button,
div[data-testid="stFileUploader"] button[kind="secondary"],
div[data-testid="stFileUploader"] button {{
    background: #00838f !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 22px !important;
    padding: 0.5rem 1.8rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    margin-top: 0.6rem !important;
    cursor: pointer !important;
    letter-spacing: 0.3px !important;
}}
div[data-testid="stFileUploaderDropzone"] button:hover,
div[data-testid="stFileUploader"] button:hover {{
    background: #006a73 !important;
}}

/* File loaded badge */
.file-loaded {{
    background: #ecfdf5;
    border: 1px solid #86efac;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    color: #047857;
    font-size: 0.88rem;
    font-weight: 500;
    margin-top: 0.5rem;
}}

/* ══════════════════════════════════════
   VALIDATE BUTTON
   ══════════════════════════════════════ */
.stButton > button {{
    background: #00838f !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.9rem 2rem !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
    width: 100% !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    transition: all 0.2s ease !important;
    margin-top: 0.5rem !important;
}}
.stButton > button:hover {{
    background: #006064 !important;
    box-shadow: 0 6px 20px rgba(0,131,143,0.30) !important;
    transform: translateY(-1px) !important;
}}

/* ══════════════════════════════════════
   TABS
   ══════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 2px solid #e2e8f0;
    background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
    padding: 0.6rem 1.4rem;
    font-size: 0.95rem;
    color: #7a8a9a;
    font-weight: 500;
    background: transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color: #00838f !important;
    border-bottom-color: #00838f !important;
    font-weight: 700 !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
    padding-top: 1.5rem !important;
}}

/* ══════════════════════════════════════
   STATUS / ALERTS / METRICS / TABLES
   ══════════════════════════════════════ */
.status-pass {{
    background: #e6f7ed; color: #047857;
    padding: 0.2rem 0.7rem; border-radius: 4px;
    font-weight: 600; font-size: 0.8rem; border: 1px solid #a7f3d0;
}}
.status-fail {{
    background: #fef2f2; color: #b91c1c;
    padding: 0.2rem 0.7rem; border-radius: 4px;
    font-weight: 600; font-size: 0.8rem; border: 1px solid #fecaca;
}}
.status-review {{
    background: #fffbeb; color: #92400e;
    padding: 0.2rem 0.7rem; border-radius: 4px;
    font-weight: 600; font-size: 0.8rem; border: 1px solid #fde68a;
}}

.alert-success {{
    background: #ecfdf5; border-left: 4px solid #10b981;
    border-radius: 8px; padding: 0.9rem 1.2rem;
    margin: 0.5rem 0; color: #065f46; font-size: 0.88rem;
}}
.alert-error {{
    background: #fef2f2; border-left: 4px solid #ef4444;
    border-radius: 8px; padding: 0.9rem 1.2rem;
    margin: 0.5rem 0; color: #7f1d1d; font-size: 0.88rem;
}}
.alert-warning {{
    background: #fffbeb; border-left: 4px solid #f59e0b;
    border-radius: 8px; padding: 0.9rem 1.2rem;
    margin: 0.5rem 0; color: #78350f; font-size: 0.88rem;
}}
.alert-info {{
    background: #e0f7fa; border-left: 4px solid #00838f;
    border-radius: 8px; padding: 0.9rem 1.2rem;
    margin: 0.5rem 0; color: #004d54; font-size: 0.88rem;
}}

.metric-card {{
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 1rem 1.2rem;
    text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}}
.metric-card .label {{
    color: #6b7b8d; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.3rem;
}}
.metric-card .value {{
    color: #1a1a2e; font-size: 1.6rem; font-weight: 700;
}}

.section-header {{
    color: #1a1a2e; font-size: 1.1rem; font-weight: 600;
    margin: 1.2rem 0 0.6rem 0; padding-bottom: 0.4rem;
    border-bottom: 2px solid #00838f;
}}

.comparison-table {{
    width: 100%; border-collapse: collapse; font-size: 0.85rem;
    margin-top: 0.5rem; background: #ffffff; border-radius: 10px;
    overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}
.comparison-table th {{
    background: #e0f2f4; color: #00606a;
    padding: 0.6rem 0.8rem; text-align: left;
    font-weight: 600; border-bottom: 2px solid rgba(0,131,143,0.2);
}}
.comparison-table td {{
    padding: 0.5rem 0.8rem; border-bottom: 1px solid #f0f0f0; color: #334155;
}}
.comparison-table tr:hover {{ background: #f8fdfd; }}

.getting-started {{
    background: #ffffff; border: 1px dashed #c5cdd5;
    border-radius: 14px; padding: 2rem 2.5rem;
    text-align: center; margin: 1rem 0;
}}
.getting-started h4 {{ color: #00838f; margin: 0 0 0.5rem 0; font-size: 1.1rem; }}
.getting-started p {{ color: #7a8a9a; font-size: 0.9rem; margin: 0; }}

/* Progress bar */
.stProgress > div > div > div > div {{
    background-color: #00838f !important;
}}

/* Misc */
div[data-baseweb="select"] {{ background: #ffffff; }}
.stDataFrame {{ background: #ffffff; border-radius: 10px; }}
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
_logo_tag = (
    f'<img class="ixom-logo" src="{_logo_src}" alt="IXOM">'
    if _logo_src
    else '<div style="font-size:2rem;font-weight:800;color:#004D54;letter-spacing:4px;margin-bottom:1rem;">IXOM</div>'
)
st.markdown(
    f"""
<div class="hero-wrap">
    {_logo_tag}
    <h1>Intelligent Document Verification</h1>
    <p class="subtitle">Automated Supplier Certificate Validation Engine</p>
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

    col_spec, col_cert = st.columns(2, gap="large")

    # ── Left: Product Specification Upload ──
    with col_spec:
        with st.container(border=True):
            st.markdown(
                '<p class="upload-title">Product Specification</p>',
                unsafe_allow_html=True,
            )
            spec_file = st.file_uploader(
                "Upload spec",
                type=["pdf"],
                key="spec_upload",
                label_visibility="collapsed",
            )
            spec_path = None
            if spec_file:
                spec_path = save_upload(spec_file)
                st.markdown(
                    f'<div class="file-loaded">&#10003; Loaded: {spec_file.name}</div>',
                    unsafe_allow_html=True,
                )

    # ── Right: Supplier Certificate Upload ──
    with col_cert:
        with st.container(border=True):
            st.markdown(
                '<p class="upload-title">Supplier Certificate</p>',
                unsafe_allow_html=True,
            )
            cert_file = st.file_uploader(
                "Upload cert",
                type=["pdf"],
                key="cert_upload",
                label_visibility="collapsed",
            )
            cert_path = None
            if cert_file:
                cert_path = save_upload(cert_file)
                st.markdown(
                    f'<div class="file-loaded">&#10003; Uploaded: {cert_file.name}</div>',
                    unsafe_allow_html=True,
                )

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
        if st.button("VALIDATE CERTIFICATE", use_container_width=True):

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
                n_not_in_cert = sum(
                    1 for d in details if d.get("status", "").upper() == "NOT_IN_CERT"
                )

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
                    f'<div class="alert-warning" style="margin-top:0.3rem;">'
                    f"<strong>Reason:</strong> {reason}</div>",
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
                    f'<div class="metric-card">'
                    f'<div class="label">{label}</div>'
                    f'<div class="value">{val}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Parameter details table
            if details:
                st.markdown(
                    '<div class="section-header">Parameter Details</div>',
                    unsafe_allow_html=True,
                )
                rows = ""
                for d in details:
                    s = d.get("status", "REVIEW").upper()
                    badge = status_badge(s)
                    param = d.get("parameter", "") or d.get("spec_parameter", "—")
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
                    rows += (
                        f"<tr><td>{badge}</td><td>{param}</td>"
                        f"<td>{spec_range}</td><td>{spec_val}</td>"
                        f"<td>{cert_val}</td><td>{comment}</td></tr>"
                    )

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
                st.markdown(
                    '<div class="section-header">Critical Issues</div>',
                    unsafe_allow_html=True,
                )
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
                st.markdown(
                    '<div class="section-header">Items for Review</div>',
                    unsafe_allow_html=True,
                )
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
    st.markdown(
        '<div class="section-header">Audit History</div>',
        unsafe_allow_html=True,
    )

    log_path = str(config.AUDIT_LOG)
    if not os.path.exists(log_path):
        st.markdown(
            '<div class="alert-info">No audit records yet. Validate a certificate to create the first entry.</div>',
            unsafe_allow_html=True,
        )
    else:
        df = pd.read_csv(log_path)

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            statuses = (
                ["ALL"] + sorted(df["Status"].dropna().unique().tolist())
                if "Status" in df.columns
                else ["ALL"]
            )
            sel_status = st.selectbox("Filter by Status", statuses)
        with col_f2:
            cert_types = (
                ["ALL"] + sorted(df["Cert_Type"].dropna().unique().tolist())
                if "Cert_Type" in df.columns
                else ["ALL"]
            )
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
        n_p = (
            len(filtered[filtered["Status"] == "PASS"])
            if "Status" in filtered.columns
            else 0
        )
        n_f = (
            len(filtered[filtered["Status"] == "FAIL"])
            if "Status" in filtered.columns
            else 0
        )
        n_r = (
            len(filtered[filtered["Status"] == "REVIEW"])
            if "Status" in filtered.columns
            else 0
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        for col, lbl, v in [
            (mc1, "TOTAL", total),
            (mc2, "PASSED", n_p),
            (mc3, "FAILED", n_f),
            (mc4, "REVIEW", n_r),
        ]:
            col.markdown(
                f'<div class="metric-card">'
                f'<div class="label">{lbl}</div>'
                f'<div class="value">{v}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<br><small>Showing {len(filtered)} of {len(df)} records</small>",
            unsafe_allow_html=True,
        )
        st.dataframe(filtered, use_container_width=True, hide_index=True)

# ── Footer ──────────────────────────────────────────────────────────────
st.markdown(
    """
<div style="text-align:center; color:#94a3b8; font-size:0.75rem; margin-top:2.5rem; padding-top:1rem; border-top:1px solid #e2e8f0;">
    Intelligent Document Verification
</div>
""",
    unsafe_allow_html=True,
)
