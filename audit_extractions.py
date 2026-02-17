"""Audit all golden test extraction pairs."""
import json

def show_params(label, data, mode="spec"):
    params = data.get("parameters", [])
    print(f"=== {label} ({len(params)} params) ===")
    for p in params:
        name = p.get("name", "")
        if mode == "spec":
            mn = p.get("min_limit", "")
            mx = p.get("max_limit", "")
            val = p.get("value", "")
            unit = p.get("unit", "")
            print(f"  {name:45s} min={mn:10s} max={mx:10s} val={val:30s} unit={unit}")
        else:
            val = p.get("value", "")
            unit = p.get("unit", "")
            print(f"  {name:45s} val={val:20s} unit={unit}")

# 1. Acetic Acid
print("=" * 80)
print("GOLDEN PAIR 1: Acetic Acid 20%")
print("=" * 80)
with open("outputs/structured_json/Acetic Acid 20 Prem Grade Oct24_spec.json") as f:
    show_params("SPEC", json.load(f), "spec")
print()
with open("outputs/structured_json/000D3AD1FF1D1EEFBCA147C86F308999_coa.json") as f:
    show_params("COA", json.load(f), "cert")
print()
with open("outputs/structured_json/000D3AD1FF1D1FE180DC8E687249C9AB_coca.json") as f:
    d = json.load(f)
    show_params("COCA", d, "cert")
    print(f"  compliance_statement: {d.get('compliance_statement', 'NONE')}")

# 2. Aqua Ammonia
print()
print("=" * 80)
print("GOLDEN PAIR 2: Aqua Ammonia 25%")
print("=" * 80)
with open("outputs/structured_json/Aqua Ammonia 25 Prem Grade Aug 24_spec.json") as f:
    show_params("SPEC", json.load(f), "spec")
print()
with open("outputs/structured_json/000D3AD1FF1D1EEC97ABB595B16C897B_coa.json") as f:
    show_params("COA", json.load(f), "cert")

# 3. Alum Sulphate
print()
print("=" * 80)
print("GOLDEN PAIR 3: Aluminium Sulphate Liquid")
print("=" * 80)
with open("outputs/structured_json/ALUSUL08 Product Specification Nov 2022_spec.json") as f:
    show_params("SPEC", json.load(f), "spec")
print()
with open("outputs/structured_json/000D3AD1FF1D1FE0A7E30961C8F489A6_coa.json") as f:
    show_params("COA", json.load(f), "cert")
print()
with open("outputs/structured_json/000D3AD1FF1D1FE0BE9DF7DEA08129AA_coc.json") as f:
    d = json.load(f)
    show_params("COC", d, "cert")
    print(f"  compliance_statement: {d.get('compliance_statement', 'NONE')}")
