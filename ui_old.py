"""
Intelligent Safety Net — Streamlit Dashboard (Phase 0 UI)

Provides:
- Audit log table with traffic-light status indicators
- Filtering by Status, Industry, Certificate Type, Model
- Per-parameter drill-down for selected rows
- Extracted JSON viewer (spec vs cert side-by-side)

Run: streamlit run ui.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ─── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Intelligent Safety Net",
    page_icon="🛡️",
    layout="wide",
)

# ─── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
AUDIT_LOG = PROJECT_ROOT / "logs" / "audit_log.csv"
JSON_DIR = PROJECT_ROOT / "outputs" / "structured_json"
MAPPING_FILE = PROJECT_ROOT / "data" / "mapping.xlsx"

# ─── Color Mapping ───────────────────────────────────────────────────
STATUS_COLORS = {
    "PASS": "#28a745",      # Green
    "FAIL": "#dc3545",      # Red
    "REVIEW": "#ffc107",    # Amber
    "ERROR": "#6c757d",     # Grey
}

STATUS_ICONS = {
    "PASS": "✅",
    "FAIL": "❌",
    "REVIEW": "🔍",
    "ERROR": "⚠️",
}


def color_status(val):
    """Apply color to status cells."""
    color = STATUS_COLORS.get(val, "#000")
    return f"background-color: {color}; color: white; font-weight: bold; text-align: center;"


# ─── Header ──────────────────────────────────────────────────────────
st.title("🛡️ Intelligent Safety Net — PoC Dashboard")
st.markdown("**Phase 0** — Local Validation Engine | IXOM Product Safety Verification")

# ─── Load Data ────────────────────────────────────────────────────────
if not AUDIT_LOG.exists():
    st.warning("⚠️ No audit log found. Run `python main.py` first to generate results.")
    st.info(f"Expected path: `{AUDIT_LOG}`")
    st.stop()

log = pd.read_csv(AUDIT_LOG)

if log.empty:
    st.warning("Audit log is empty. Run the batch processor first.")
    st.stop()

# ─── Summary Metrics ─────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)

total = len(log)
passed = len(log[log["Status"] == "PASS"])
failed = len(log[log["Status"] == "FAIL"])
review = len(log[log["Status"] == "REVIEW"])
errors = len(log[log["Status"] == "ERROR"])

col1.metric("Total Processed", total)
col2.metric("✅ Passed", passed, delta=f"{passed/total*100:.0f}%" if total else "0%")
col3.metric("❌ Failed", failed)
col4.metric("🔍 Review", review)
col5.metric("⚠️ Errors", errors)

# ─── Filters ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Audit Log")

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    status_filter = st.selectbox(
        "Filter by Status",
        ["ALL"] + sorted(log["Status"].unique().tolist()),
    )

with filter_col2:
    cert_types = ["ALL"]
    if "Cert_Type" in log.columns:
        cert_types += sorted(log["Cert_Type"].dropna().unique().tolist())
    cert_filter = st.selectbox("Filter by Cert Type", cert_types)

with filter_col3:
    models = ["ALL"]
    if "Model" in log.columns:
        models += sorted(log["Model"].dropna().unique().tolist())
    model_filter = st.selectbox("Filter by Model", models)

# Apply filters
filtered = log.copy()
if status_filter != "ALL":
    filtered = filtered[filtered["Status"] == status_filter]
if cert_filter != "ALL":
    filtered = filtered[filtered["Cert_Type"] == cert_filter]
if model_filter != "ALL":
    filtered = filtered[filtered["Model"] == model_filter]

# ─── Display Table ───────────────────────────────────────────────────
display_cols = [
    "Spec_File", "Cert_File", "Cert_Type", "Status", "Product_Name",
    "Material_Number", "Batch_Number", "Confidence",
    "Parameters_Checked", "Parameters_Passed", "Parameters_Failed",
    "Parameters_Missing", "Reason",
]
display_cols = [c for c in display_cols if c in filtered.columns]

styled = filtered[display_cols].style.map(
    color_status, subset=["Status"] if "Status" in display_cols else []
)
st.dataframe(styled, width="stretch", height=400)

st.caption(f"Showing {len(filtered)} of {total} records")

# ─── Detail View ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔍 Detail View")

if not filtered.empty:
    row_options = []
    for idx, row in filtered.iterrows():
        icon = STATUS_ICONS.get(row.get("Status", ""), "")
        label = f"{icon} {row.get('Spec_File', 'N/A')} ↔ {row.get('Cert_File', 'N/A')} ({row.get('Cert_Type', '')})"
        row_options.append(label)

    selected_label = st.selectbox("Select a pair to inspect", row_options)
    selected_idx = row_options.index(selected_label)
    selected_row = filtered.iloc[selected_idx]

    # Show details
    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:
        st.markdown("**Specification**")
        spec_stem = Path(str(selected_row.get("Spec_File", ""))).stem
        spec_json = JSON_DIR / f"{spec_stem}_spec.json"
        if spec_json.exists():
            with open(spec_json) as f:
                spec_data = json.load(f)
            st.json(spec_data)
        else:
            st.info(f"No extracted JSON found: {spec_json.name}")

    with detail_col2:
        st.markdown("**Certificate**")
        cert_stem = Path(str(selected_row.get("Cert_File", ""))).stem
        cert_type_lower = str(selected_row.get("Cert_Type", "coa")).lower()
        cert_json = JSON_DIR / f"{cert_stem}_{cert_type_lower}.json"
        if cert_json.exists():
            with open(cert_json) as f:
                cert_data = json.load(f)
            st.json(cert_data)
        else:
            st.info(f"No extracted JSON found: {cert_json.name}")

    # Show comparison details if available
    st.markdown("**Result Details**")
    st.write(f"**Status:** {STATUS_ICONS.get(selected_row.get('Status', ''), '')} {selected_row.get('Status', '')}")
    st.write(f"**Reason:** {selected_row.get('Reason', 'N/A')}")
    st.write(f"**Model:** {selected_row.get('Model', 'N/A')}")
    st.write(f"**Confidence:** {selected_row.get('Confidence', 'N/A')}")

# ─── Footer ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Intelligent Safety Net v0.1 — Phase 0 PoC | IXOM Product Validation")
