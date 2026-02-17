"""Quick test script for the AI-powered comparator."""
import sys, json
sys.path.insert(0, ".")
import config
from core.comparator import compare_documents

# Test 1: Correct pair — Acetic Acid spec + Acetic Acid COA
print("=" * 70)
print("TEST 1: CORRECT PAIR — Acetic Acid Spec + Acetic Acid COA")
print("=" * 70)

s = json.load(open("outputs/structured_json/Acetic Acid 20 Prem Grade Oct24_spec.json"))
c = json.load(open("outputs/structured_json/000D3AD1FF1D1EEFBCA147C86F308999_coa.json"))

print(f"Spec product: {s['product_name']}")
print(f"Cert product: {c['product_name']}")
print(f"Spec params:  {[p['name'] for p in s['parameters']]}")
print(f"Cert params:  {[p['name'] for p in c['parameters']]}")
print()

r = compare_documents(s, c, cert_type="COA", model="gpt-4o")
print(f"STATUS: {r['status']}")
print(f"REASON: {r['reason']}")
print(f"Checked={r['parameters_checked']} Pass={r['parameters_passed']} Fail={r['parameters_failed']} Review={r['parameters_review']}")
print()
for d in r.get("details", []):
    print(f"  [{d['status']:6s}] {d.get('parameter','')} -> {d.get('cert_parameter','')} "
          f"| cert_val={d.get('cert_value','')} | {d.get('reason','')}")

# Test 2: WRONG pair — Acetic Acid spec + Zinc Gluconate COA
print()
print("=" * 70)
print("TEST 2: WRONG PAIR — Acetic Acid Spec + Zinc Gluconate COA (SHOULD FAIL)")
print("=" * 70)

# The Zinc Gluconate cert was uploaded from the UI — check for cached extraction
import os
zinc_cert_path = config.SOURCE_PDFS_DIR / "000D3AD1FF1D1EEE90C02822D623C985.pdf"
zinc_json = None
for f in os.listdir("outputs/structured_json"):
    if "EEE90C02822D623C985" in f or "zingl" in f.lower():
        zinc_json = f"outputs/structured_json/{f}"
        break

# Also check tmp files from UI upload
for f in os.listdir("outputs/structured_json"):
    if f.startswith("tmp") and f.endswith("_coa.json"):
        data = json.load(open(f"outputs/structured_json/{f}"))
        if "zinc" in data.get("product_name", "").lower() or "gluconate" in data.get("product_name", "").lower():
            zinc_json = f"outputs/structured_json/{f}"
            break

if zinc_json:
    c2 = json.load(open(zinc_json))
    print(f"Spec product: {s['product_name']}")
    print(f"Cert product: {c2['product_name']}")
    print()
    r2 = compare_documents(s, c2, cert_type="COA", model="gpt-4o")
    print(f"STATUS: {r2['status']}")
    print(f"REASON: {r2['reason']}")
    print(f"Product mismatch: {r2.get('product_mismatch', False)}")
else:
    print("Zinc Gluconate cert JSON not found — extracting fresh...")
    from core.cert_extractor import extract_certificate
    c2 = extract_certificate(str(zinc_cert_path), "gpt-4o", expected_type="COA")
    print(f"Cert product: {c2['product_name']}")
    r2 = compare_documents(s, c2, cert_type="COA", model="gpt-4o")
    print(f"STATUS: {r2['status']}")
    print(f"REASON: {r2['reason']}")
    print(f"Product mismatch: {r2.get('product_mismatch', False)}")
