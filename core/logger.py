"""
Logger — Handles CSV audit logging and run summaries.

Appends results to a persistent audit_log.csv and creates per-run summaries.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import config

# ─── CSV Column Headers ──────────────────────────────────────────────
AUDIT_COLUMNS = [
    "Timestamp",
    "Spec_File",
    "Cert_File",
    "Cert_Type",
    "Model",
    "Doc_Type_Detected",
    "Product_Name",
    "Material_Number",
    "Batch_Number",
    "Status",
    "Reason",
    "Confidence",
    "Parameters_Checked",
    "Parameters_Passed",
    "Parameters_Failed",
    "Parameters_Missing",
]


def _ensure_audit_log():
    """Create audit log file with headers if it doesn't exist."""
    if not config.AUDIT_LOG.exists():
        config.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(config.AUDIT_LOG, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(AUDIT_COLUMNS)


def log_result(
    spec_file: str,
    cert_file: str,
    cert_type: str,
    model: str,
    classification: Dict,
    comparison: Dict,
    material_number: str = "",
) -> None:
    """
    Append a single comparison result to the audit log.

    Args:
        spec_file: Spec PDF filename
        cert_file: Certificate PDF filename
        cert_type: COA / COCA / COC
        model: Model used for extraction
        classification: Output from document_classifier
        comparison: Output from comparator
        material_number: Material number from mapping
    """
    _ensure_audit_log()

    row = [
        datetime.now().isoformat(),
        spec_file,
        cert_file,
        cert_type,
        model,
        classification.get("document_type", ""),
        comparison.get("product_name", ""),
        material_number,
        comparison.get("batch_number", ""),
        comparison.get("status", "ERROR"),
        comparison.get("reason", "")[:500],  # Truncate long reasons
        classification.get("confidence_score", 0.0),
        comparison.get("parameters_checked", 0),
        comparison.get("parameters_passed", 0),
        comparison.get("parameters_failed", 0),
        comparison.get("parameters_review", 0),
    ]

    with open(config.AUDIT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    # Also print to console
    status = comparison.get("status", "ERROR")
    status_icon = {"PASS": "✅", "FAIL": "❌", "REVIEW": "🔍"}.get(status, "⚠️")
    print(f"  {status_icon} [{status}] {spec_file} ↔ {cert_file} ({cert_type})")
    if comparison.get("reason"):
        print(f"     Reason: {comparison['reason'][:120]}")


def log_error(
    spec_file: str,
    cert_file: str,
    cert_type: str,
    model: str,
    error_msg: str,
    material_number: str = "",
) -> None:
    """Log an error that prevented processing."""
    _ensure_audit_log()

    row = [
        datetime.now().isoformat(),
        spec_file,
        cert_file,
        cert_type,
        model,
        "ERROR",
        "",
        material_number,
        "",
        "ERROR",
        error_msg[:500],
        0.0,
        0, 0, 0, 0,
    ]

    with open(config.AUDIT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    print(f"  ⚠️ [ERROR] {spec_file} ↔ {cert_file}: {error_msg[:100]}")


def write_run_summary(results: list, model: str) -> str:
    """
    Write a per-run summary CSV file.

    Args:
        results: List of comparison result dicts
        model: Model used

    Returns:
        Path to the summary file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = config.LOGS_DIR / f"run_summary_{timestamp}.csv"

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Run Summary", f"Model: {model}", f"Time: {timestamp}"])
        writer.writerow([])
        writer.writerow(["Metric", "Count"])

        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "PASS")
        failed = sum(1 for r in results if r.get("status") == "FAIL")
        review = sum(1 for r in results if r.get("status") == "REVIEW")
        errors = sum(1 for r in results if r.get("status") == "ERROR")

        writer.writerow(["Total Processed", total])
        writer.writerow(["Passed", passed])
        writer.writerow(["Failed", failed])
        writer.writerow(["Review Required", review])
        writer.writerow(["Errors", errors])
        writer.writerow([])
        writer.writerow(["Pass Rate", f"{passed/total*100:.1f}%" if total else "N/A"])

    return str(summary_path)


def print_summary(results: list):
    """Print a formatted summary table to console."""
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    review = sum(1 for r in results if r.get("status") == "REVIEW")
    errors = sum(1 for r in results if r.get("status") == "ERROR")

    print("\n" + "=" * 60)
    print("  INTELLIGENT SAFETY NET — RUN SUMMARY")
    print("=" * 60)
    print(f"  Total Processed:  {total}")
    print(f"  ✅ Passed:        {passed}")
    print(f"  ❌ Failed:        {failed}")
    print(f"  🔍 Review:        {review}")
    print(f"  ⚠️  Errors:        {errors}")
    if total:
        print(f"  Pass Rate:        {passed/total*100:.1f}%")
    print("=" * 60)
