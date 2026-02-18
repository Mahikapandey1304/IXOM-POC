"""
Intelligent Safety Net — Main Orchestrator

Batch processes IXOM product specifications against their certificates (COA/COCA/COC)
using GPT-4o Vision for document classification and structured extraction.

Usage:
    python main.py                      # Process all mapped pairs
    python main.py --golden-test        # Process only golden test pairs (rows 1,6,11)
    python main.py --model gpt-4o-mini  # Override model
    python main.py --row 3              # Process a specific row only
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import config
from model_switcher import get_model
from core.document_classifier import classify_document
from core.spec_extractor import extract_spec
from core.cert_extractor import extract_certificate
from core.comparator import compare_documents
from core.logger import log_result, log_error, write_run_summary, print_summary
from core.retry_config import retry_file_io


def resolve_pdf_path(filename: str, is_spec: bool = False) -> str:
    """
    Resolve the full path to a PDF file.
    Checks data/ subdirs first, then falls back to source pdfs/ folder.
    """
    if not filename or pd.isna(filename):
        return None

    filename = str(filename).strip()
    if not filename:
        return None

    # Check in organized data dirs
    if is_spec:
        local_path = config.SPECS_DIR / filename
    else:
        local_path = config.CERTS_DIR / filename

    if local_path.exists():
        return str(local_path)

    # Fallback to original pdfs/ folder
    source_path = config.SOURCE_PDFS_DIR / filename
    if source_path.exists():
        return str(source_path)

    return None


def process_single_pair(
    spec_file: str,
    cert_file: str,
    cert_type: str,
    model: str,
    material_number: str = "",
) -> dict:
    """
    Process a single spec ↔ certificate pair through the full pipeline:
    Classify → Extract Spec → Extract Cert → Compare → Log
    """
    spec_path = resolve_pdf_path(spec_file, is_spec=True)
    cert_path = resolve_pdf_path(cert_file, is_spec=False)

    if not spec_path:
        error_msg = f"Spec file not found: {spec_file}"
        log_error(spec_file, cert_file, cert_type, model, error_msg, material_number)
        return {"status": "ERROR", "reason": error_msg}

    if not cert_path:
        error_msg = f"Certificate file not found: {cert_file}"
        log_error(spec_file, cert_file, cert_type, model, error_msg, material_number)
        return {"status": "ERROR", "reason": error_msg}

    try:
        # Step 1: Classify the certificate document
        print(f"\n  📄 Classifying: {cert_file}")
        classification = classify_document(cert_path, model)
        detected_type = classification.get("document_type", "Unknown")
        confidence = classification.get("confidence_score", 0.0)
        print(f"     → Type: {detected_type} (confidence: {confidence:.2f})")

        # Step 2: Extract spec parameters
        print(f"  📋 Extracting spec: {spec_file}")
        spec_data = extract_spec(spec_path, model)
        n_spec_params = len(spec_data.get("parameters", []))
        print(f"     → Extracted {n_spec_params} parameters")

        # Step 3: Extract certificate data
        print(f"  🔬 Extracting cert: {cert_file} ({cert_type})")
        cert_data = extract_certificate(cert_path, model, expected_type=cert_type)
        n_cert_params = len(cert_data.get("parameters", []))
        print(f"     → Extracted {n_cert_params} parameters, batch: {cert_data.get('batch_number', 'N/A')}")

        # Step 4: Compare (AI-powered alignment)
        print(f"  ⚖️  Comparing (AI-powered alignment)...")
        comparison = compare_documents(spec_data, cert_data, cert_type=cert_type, model=model)

        # Step 5: Log
        log_result(
            spec_file, cert_file, cert_type, model,
            classification, comparison, material_number
        )

        return comparison

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_error(spec_file, cert_file, cert_type, model, error_msg, material_number)
        print(f"  ❌ Error processing {cert_file}: {error_msg}")
        return {"status": "ERROR", "reason": error_msg}


def main():
    parser = argparse.ArgumentParser(description="Intelligent Safety Net — Batch Processor")
    parser.add_argument("--golden-test", action="store_true",
                        help="Process only golden test pairs (rows 1, 6, 11)")
    parser.add_argument("--model", type=str, default=None,
                        help="Override model (e.g., gpt-4o-mini)")
    parser.add_argument("--row", type=int, default=None,
                        help="Process a specific row number (S.N) only")
    args = parser.parse_args()

    model = args.model or get_model()

    print("=" * 60)
    print("  INTELLIGENT SAFETY NET — Phase 0 PoC")
    print(f"  Model: {model}")
    print(f"  Mapping: {config.MAPPING_FILE}")
    print("=" * 60)

    # Load mapping
    if not config.MAPPING_FILE.exists():
        print(f"\n❌ Mapping file not found: {config.MAPPING_FILE}")
        print("   Run: python build_mapping.py")
        sys.exit(1)

    @retry_file_io
    def _load_mapping():
        return pd.read_excel(config.MAPPING_FILE)
    
    mapping = _load_mapping()
    print(f"\n  Loaded {len(mapping)} product rows from mapping")

    # Filter rows based on CLI flags
    if args.golden_test:
        mapping = mapping[mapping["SN"].isin(config.GOLDEN_TEST_ROWS)]
        print(f"  🏆 Golden test mode: processing rows {config.GOLDEN_TEST_ROWS}")
    elif args.row:
        mapping = mapping[mapping["SN"] == args.row]
        print(f"  Processing single row: {args.row}")

    if mapping.empty:
        print("  ⚠️  No rows to process.")
        sys.exit(0)

    # Process each row — iterate over cert type columns
    all_results = []
    cert_columns = {
        "COA_File": "COA",
        "COCA_File": "COCA",
        "COC_File": "COC",
    }

    start_time = time.time()

    for idx, row in mapping.iterrows():
        sn = row.get("SN", idx + 1)
        spec_file = row.get("Spec_File", "")
        material = row.get("Material_Number", "")
        industry = row.get("Industry", "")

        print(f"\n{'─' * 60}")
        print(f"  Row {sn}: {material} ({industry})")
        print(f"  Spec: {spec_file}")

        if not spec_file or pd.isna(spec_file):
            print("  ⚠️  No spec file — skipping")
            continue

        for col_name, cert_type in cert_columns.items():
            cert_file = row.get(col_name, "")
            if not cert_file or pd.isna(cert_file):
                continue

            result = process_single_pair(
                spec_file=spec_file,
                cert_file=cert_file,
                cert_type=cert_type,
                model=model,
                material_number=material,
            )
            all_results.append(result)

    elapsed = time.time() - start_time

    # Summary
    print_summary(all_results)
    summary_path = write_run_summary(all_results, model)
    print(f"\n  📁 Audit log: {config.AUDIT_LOG}")
    print(f"  📁 Run summary: {summary_path}")
    print(f"  ⏱️  Total time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
