"""
Build Mapping — Generates data/mapping.xlsx from the IXOM product-document mapping.

This encodes the 15-row pairing table provided by the team, mapping each product's
specification PDF to its associated certificate PDFs (COA, COCA, COC).
"""

import pandas as pd
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_PATH = PROJECT_ROOT / "data" / "mapping.xlsx"


def build_mapping():
    """Create the mapping Excel file from the known IXOM product-document pairs."""

    data = [
        {
            "SN": 1,
            "Industry": "Food, Beverage & Nutrition",
            "Material_Number": "ACEACI20FG-15L",
            "Spec_File": "Acetic Acid 20 Prem Grade Oct24.pdf",
            "COA_File": "000D3AD1FF1D1EEFBCA147C86F308999.pdf",
            "COCA_File": "000D3AD1FF1D1FE180DC8E687249C9AB.pdf",
            "COC_File": "",
        },
        {
            "SN": 2,
            "Industry": "Food, Beverage & Nutrition",
            "Material_Number": "ACETIC80FG-200L",
            "Spec_File": "Acetic Acid 80 Prem Grade Aug 25 (1).pdf",
            "COA_File": "",
            "COCA_File": "000D3AD1FF1D1EEFBFBF32029B5C499A.pdf",
            "COC_File": "",
        },
        {
            "SN": 3,
            "Industry": "Food, Beverage & Nutrition",
            "Material_Number": "REZOLV25-B",
            "Spec_File": "Rezolv 25 Product Spec_Aug2028.pdf",
            "COA_File": "000D3AD1FFC61EEFA9FC65EA780C8994.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 4,
            "Industry": "Food, Beverage & Nutrition",
            "Material_Number": "TOFLANAT48162-1000",
            "Spec_File": "TOFLANAT48162-15 IXOM Product Specification Aug 2023.pdf",
            "COA_File": "000D3AD1FF1D1FE181C76E9ACDD6A9AC.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 5,
            "Industry": "Food, Beverage & Nutrition",
            "Material_Number": "ZYDOX31-1000L",
            "Spec_File": "Zydox 31 May 25.pdf",
            "COA_File": "000D3AD1FF1D1EEEB9E5FA1CDB30E98A.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 6,
            "Industry": "Health & Personal Care",
            "Material_Number": "AQUAMM25-190S",
            "Spec_File": "Aqua Ammonia 25 Prem Grade Aug 24.pdf",
            "COA_File": "000D3AD1FF1D1EEC97ABB595B16C897B.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 7,
            "Industry": "Health & Personal Care",
            "Material_Number": "LUMGLO-20",
            "Spec_File": "SPEC Omega Max Rev.04.pdf",
            "COA_File": "000D3AD1FF1D1EEEA7FAF4EF72B0E987.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 8,
            "Industry": "Health & Personal Care",
            "Material_Number": "ODOT60219A-20",
            "Spec_File": "ODOT60219A Ixom Product Spec Approved by Ai Rin APR 2025.pdf",
            "COA_File": "000D3AD1FFC61EECACAB24C389E6097E.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 9,
            "Industry": "Health & Personal Care",
            "Material_Number": "PEAOILR-190",
            "Spec_File": "PEAOILR IXOM Product Specification 2017 (Henry Lalmotte 2014).pdf",
            "COA_File": "000D3AD1FF1D1EEB9C9B2CEDD325E974.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 10,
            "Industry": "Health & Personal Care",
            "Material_Number": "ZINGLUFCC-25",
            "Spec_File": "ZINGLUFCC-25 Product Specification June 2023.pdf",
            "COA_File": "000D3AD1FF1D1EEE90C02822D623C985.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 11,
            "Industry": "Water",
            "Material_Number": "ALUSUL08-1000NR",
            "Spec_File": "ALUSUL08 Product Specification Nov 2022.pdf",
            "COA_File": "000D3AD1FF1D1FE0A7E30961C8F489A6.pdf",
            "COCA_File": "",
            "COC_File": "000D3AD1FF1D1FE0BE9DF7DEA08129AA.pdf",
        },
        {
            "SN": 12,
            "Industry": "Water",
            "Material_Number": "ALUSUL-1320BBOX",
            "Spec_File": "Ixom Product Specification ALUSUL- MAY 2025 v4.pdf",
            "COA_File": "000D3AD1FF1D1EEBA19F4D24BC636976.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 13,
            "Industry": "Water",
            "Material_Number": "SODHYP13-1000BB",
            "Spec_File": "SODHYP13 Product Specification Jan 2025.pdf",
            "COA_File": "000D3AD1FF1D1FE09CE28751E5D169A2.pdf",
            "COCA_File": "",
            "COC_File": "000D3AD1FFC61FE0A682A697453AC9A6.pdf",
        },
        {
            "SN": 14,
            "Industry": "Water",
            "Material_Number": "SOL250AD-20",
            "Spec_File": "IXOM Product Spec - Solipac v5 April 2023.pdf",
            "COA_File": "000D3AD1FF1D1EEC929D91CF6A8AA97B.pdf",
            "COCA_File": "",
            "COC_File": "",
        },
        {
            "SN": 15,
            "Industry": "Water",
            "Material_Number": "PAC10LB-1000",
            "Spec_File": "PAC10LB Product Specification.pdf",
            "COA_File": "000D3AD1FFC61EEFAC90A9690D27E994.pdf",
            "COCA_File": "",
            "COC_File": "000D3AD1FF1D1FE09493E81442EF099D.pdf",
        },
    ]

    df = pd.DataFrame(data)

    # Save to Excel
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT_PATH, index=False, sheet_name="Mapping")
    print(f"✅ Mapping file created: {OUTPUT_PATH}")
    print(f"   {len(df)} products mapped")

    # Print summary
    print(f"\n   Industries:")
    for industry, count in df["Industry"].value_counts().items():
        print(f"     • {industry}: {count} products")

    coa_count = df["COA_File"].apply(lambda x: bool(x)).sum()
    coca_count = df["COCA_File"].apply(lambda x: bool(x)).sum()
    coc_count = df["COC_File"].apply(lambda x: bool(x)).sum()
    print(f"\n   Certificate coverage:")
    print(f"     • COA:  {coa_count}/15")
    print(f"     • COCA: {coca_count}/15")
    print(f"     • COC:  {coc_count}/15")
    print(f"     • Total pairs to process: {coa_count + coca_count + coc_count}")


if __name__ == "__main__":
    build_mapping()
