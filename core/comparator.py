"""
Comparator Engine — Compares extracted spec parameters against certificate values.

Uses AI-powered parameter alignment (GPT-4o) to handle naming differences between
spec and cert documents, then performs numeric/qualitative validation.

Produces Pass / Fail / Review status for each parameter and overall document.
"""

import json
import re
from typing import List, Dict, Optional

from openai import OpenAI

import config
from core.unit_normalizer import (
    normalize_param_name,
    normalize_unit,
    parse_value,
    are_units_compatible,
    convert_value,
)

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ─── Product Mismatch Detection ──────────────────────────────────────

def _normalize_product_tokens(name: str) -> set:
    """Extract meaningful tokens from a product name for matching."""
    if not name:
        return set()
    s = name.lower()
    # Remove common noise words
    noise = {"product", "specification", "spec", "premium", "grade", "prem",
             "grd", "ixom", "certificate", "analysis", "of", "the", "for",
             "in", "and", "a", "an", "rev", "revision", "approved", "by",
             "drums", "kg", "l", "ml", "ibc", "bulk", "non", "returnable",
             "flv10594", "flv"}
    tokens = set(re.findall(r'[a-z]+', s))
    # Also extract numbers (concentrations like 20, 25, 13)
    numbers = set(re.findall(r'\d+', s))
    return (tokens - noise) | numbers


# ─── Chemical abbreviation mappings ───────────────────────────────────
_CHEM_ALIASES = {
    "alum": "aluminium",
    "aluminum": "aluminium",
    "hypo": "hypochlorite",
    "caustic": "hydroxide",
    "soda": "sodium",
    "hcl": "hydrochloric",
    "naoh": "hydroxide",
    "ammonia": "ammonia",
    "aqueous": "aqua",
    "sulphate": "sulfate",
    "sulphuric": "sulfuric",
    "ferric": "iron",
    "pac": "aluminium",
    "naclo": "hypochlorite",
}


def _check_product_match(spec_product: str, cert_product: str) -> tuple:
    """
    Check if spec and cert are for the same product.
    This is a VERY LENIENT pre-check — designed to catch only obvious mismatches
    like completely different chemicals (e.g., Acetic Acid vs Zinc Gluconate).
    The AI comparison does the thorough check.

    Returns (is_match: bool, confidence: float, reason: str)
    """
    if not spec_product or not cert_product:
        return True, 0.5, "Cannot verify — product name missing"

    spec_tokens = _normalize_product_tokens(spec_product)
    cert_tokens = _normalize_product_tokens(cert_product)

    if not spec_tokens or not cert_tokens:
        return True, 0.5, "Cannot verify — insufficient product info"

    # Build expanded token sets with aliases
    def _expand_tokens(tokens: set) -> set:
        expanded = set(tokens)
        for t in tokens:
            if t in _CHEM_ALIASES:
                expanded.add(_CHEM_ALIASES[t])
            # Reverse lookup
            for alias, canonical in _CHEM_ALIASES.items():
                if t == canonical:
                    expanded.add(alias)
        return expanded

    spec_expanded = _expand_tokens(spec_tokens)
    cert_expanded = _expand_tokens(cert_tokens)

    # Check 1: Direct token overlap (including aliases)
    direct_overlap = spec_expanded & cert_expanded
    if direct_overlap:
        return True, 0.8, f"Token match: {', '.join(list(direct_overlap)[:5])}"

    # Check 2: Substring matching (alum ⊂ aluminium, hypo ⊂ hypochlorite)
    for st in spec_tokens:
        for ct in cert_tokens:
            if len(st) >= 3 and len(ct) >= 3:
                if st.startswith(ct) or ct.startswith(st):
                    return True, 0.7, f"Substring match: '{st}' ~ '{ct}'"

    # Check 3: Concentration number overlap
    spec_nums = set(re.findall(r'\d+', spec_product))
    cert_nums = set(re.findall(r'\d+', cert_product))
    num_overlap = spec_nums & cert_nums
    token_common = spec_tokens & cert_tokens
    total = spec_tokens | cert_tokens
    overlap_ratio = len(token_common) / len(total) if total else 0

    if num_overlap and overlap_ratio >= 0.1:
        return True, 0.6, f"Number overlap: {num_overlap}"

    # Check 4: Very strict — only flag if ZERO meaningful overlap
    # Extract 3+ char words (chemical names) from both
    spec_words = set(re.findall(r'[a-z]{3,}', spec_product.lower()))
    cert_words = set(re.findall(r'[a-z]{3,}', cert_product.lower()))
    noise_long = {"product", "specification", "premium", "grade", "certificate",
                  "analysis", "approved", "ixom", "revision", "drums", "bulk",
                  "non", "returnable", "liquid"}
    spec_words -= noise_long
    cert_words -= noise_long

    # Expand with aliases and check
    spec_words_exp = _expand_tokens(spec_words)
    cert_words_exp = _expand_tokens(cert_words)

    word_overlap = spec_words_exp & cert_words_exp
    if word_overlap:
        return True, 0.7, f"Expanded word match: {', '.join(list(word_overlap)[:5])}"

    # Substring check on longer words too
    for sw in spec_words:
        for cw in cert_words:
            if len(sw) >= 3 and len(cw) >= 3:
                if sw.startswith(cw) or cw.startswith(sw):
                    return True, 0.6, f"Word substring: '{sw}' ~ '{cw}'"

    # ZERO overlap at all — likely a genuine mismatch
    if not word_overlap and not num_overlap and not direct_overlap:
        return False, 0.1, (
            f"PRODUCT MISMATCH: Specification is for '{spec_product}' "
            f"but certificate is for '{cert_product}'"
        )

    # Uncertain — default to match and let AI decide
    return True, 0.4, "Uncertain match — AI will verify"


# ─── AI-Powered Parameter Alignment ──────────────────────────────────

AI_COMPARISON_PROMPT = """You are an expert chemical QA analyst comparing a Product Specification against a supplier certificate ({cert_type}).

Your job:
1. First check: Are both documents for the SAME product? If not, report a product mismatch.
2. For each specification parameter, find the MATCHING parameter in the certificate.
   Parameter names WILL differ between spec and cert — use your chemistry knowledge to align them.
3. Compare the certificate value against the specification limits.

═══════════════════════════════════════════════════════════════
PRODUCT MATCHING — BE GENEROUS, not strict:
═══════════════════════════════════════════════════════════════
- Supplier certs often abbreviate, reorder, or add extra info (pack sizes, codes, lot refs).
- These are ALL the SAME product:
  * "Acetic Acid 20% - Premium Grade" = "ACETIC ACID 20% FLV10594 PREMIUM GRD 15L"
  * "Aluminium Sulphate Liquid" = "LIQUID ALUM NON RETURNABLE IBC (1310 KG)"
  * "Aqua Ammonia 25%" = "AQUEOUS AMMONIA 25% in Drums 190 kg"
  * "Sodium Hypochlorite 13%" = "SODIUM HYPO 13% 1000L IBC"
  * "Zinc Gluconate" = "ZINC GLUCONATE POWDER FG"
  * "Hydrochloric Acid 33%" = "HCL 33% BULK"
  * "Sodium Hydroxide 46%" = "CAUSTIC SODA 46% LIQ"
- If the CORE chemical name and concentration match → product_match = true.
- Only set product_match = false if the products are fundamentally DIFFERENT chemicals
  (e.g., "Acetic Acid" vs "Zinc Gluconate", or "Ammonia" vs "Aluminium Sulphate").

═══════════════════════════════════════════════════════════════
PARAMETER MATCHING — names WILL differ, use chemistry knowledge:
═══════════════════════════════════════════════════════════════
- "Strength (as Acetic Acid)" = "Acid Strength (%w/w Acetic)" = "Acetic acid strength" = "Assay"
- "Specific Gravity (20/4)" = "SG (20°C)" = "Density" = "SG @25°C" = "SG (20/4°C)"
- "Appearance and Odour" = "Appearance" = "Colour and Odour" = "Color" = "Colour"
- "Strength Ammonia" = "% concentration" = "Ammonia concentration" = "NH3 content"
- "Aluminium content as Al2O3" = "Al2O3" = "Aluminum content"
- Use chemical knowledge — the same property may have MANY different names.

═══════════════════════════════════════════════════════════════
SPECIFIC GRAVITY / DENSITY TEMPERATURE NOTATION:
═══════════════════════════════════════════════════════════════
- "SG (20/4)" means "measured at 20°C, referenced to water at 4°C" — this IS the same as "SG at 20°C"
- "SG (20/4)" = "SG (20°C)" = "SG (20/4°C)" — these are ALL the same measurement. Mark PASS if value is in range.
- Only mark REVIEW for genuinely different temperatures like 15°C vs 25°C (>2°C difference).
- For small temperature differences (20°C vs 25°C), if the value is within spec limits, mark PASS.
  Only mark REVIEW if the value is very close to a limit boundary AND temperatures differ significantly.

═══════════════════════════════════════════════════════════════
UNIT EQUIVALENCES — convert before comparing:
═══════════════════════════════════════════════════════════════
- %w/w = % = wt% = weight percent
- mg/kg = ppm = mg/L (for aqueous solutions)
- g/cm³ ≈ SG (Specific Gravity is dimensionless but numerically equal to density in g/cm³)

SPECIFICATION DATA:
{spec_json}

CERTIFICATE DATA ({cert_type}):
{cert_json}

{extra_instructions}

Return ONLY valid JSON in this EXACT format:
{{
  "product_match": true or false,
  "product_match_reason": "<explain if products match or not>",
  "spec_product": "<product name from spec>",
  "cert_product": "<product name from cert>",
  "compliance_statement_present": true or false,
  "compliance_statement": "<compliance declaration text if present, else empty>",
  "parameters": [
    {{
      "spec_parameter": "<parameter name from specification>",
      "cert_parameter": "<matched parameter name from certificate, or empty if not found>",
      "spec_min": "<min limit from spec, or empty>",
      "spec_max": "<max limit from spec, or empty>",
      "spec_value": "<spec expected value if qualitative, or empty>",
      "spec_unit": "<unit from spec>",
      "cert_value": "<actual value from certificate, or empty if not found>",
      "cert_unit": "<unit from certificate>",
      "status": "PASS or FAIL or REVIEW or NOT_IN_CERT",
      "reason": "<brief explanation of the verdict>"
    }}
  ]
}}

STATUS RULES:
- PASS: Certificate value is within specification limits, OR qualitative value is acceptable
       ("Pass", "Conforms", "Complies", "Clear" etc. for appearance = PASS)
       ("ND", "Not Detected", "BDL" for impurity/contaminant parameters = PASS if max limit exists)
       SG 20/4 and SG 20°C are the SAME measurement — if value is within limits → PASS
- FAIL: Certificate value is NUMERICALLY OUTSIDE specification limits (proven by calculation)
        ONLY use FAIL when you are mathematically certain the value is out of range.
- REVIEW: Units genuinely incompatible, measurement conditions genuinely differ (>2°C temp gap),
         cert shows a range instead of a specific tested value, or ambiguous compliance.
- NOT_IN_CERT: Parameter exists in specification but has NO corresponding value in the certificate.
              Use this ONLY when no matching parameter can be found in the certificate at all.
              This is common for visual inspection items (Foreign Matter, etc.) that are
              manufacturing-floor checks and do NOT appear in lab certificates.

Be strict on FAIL (only if math proves out of range), generous on PASS for qualitative matches.
Every spec parameter MUST appear in the output, even if not found in the cert.
"""

EXTRA_COA = """This is a Certificate of Analysis (COA) which contains actual lab test results.
Compare EACH spec parameter against the actual measured value in the COA."""

EXTRA_COCA = """This is a Certificate of Compliance with Analysis (COCA).
It may contain:
- A compliance statement/declaration
- Actual test results (treat these like COA values — compare each against spec limits)
Compare ALL parameters that have values. Also note whether a compliance statement is present."""

EXTRA_COC = """This is a Certificate of Conformance (COC).
It typically contains:
- A compliance statement/declaration
- Some parameters may show specification ranges rather than individual test results
If a parameter shows a range (e.g., "7.90 - 8.20") instead of a single value:
  - If the range matches or falls within the spec range → PASS
  - If the range overlaps but extends beyond spec → REVIEW
  - If fully outside spec → FAIL
Also note whether a compliance statement is present."""


def _ai_compare(spec_data: dict, cert_data: dict, cert_type: str = "COA", model: str = None) -> dict:
    """
    Use GPT-4o to intelligently align and compare spec vs cert parameters.
    Works for all cert types: COA, COCA, COC.
    """
    model = model or config.DEFAULT_MODEL

    spec_json = json.dumps({
        "product_name": spec_data.get("product_name", ""),
        "material_number": spec_data.get("material_number", ""),
        "parameters": spec_data.get("parameters", []),
    }, indent=2)

    cert_extra = {
        "product_name": cert_data.get("product_name", ""),
        "batch_number": cert_data.get("batch_number", ""),
        "parameters": cert_data.get("parameters", []),
    }
    # Include compliance statement for COCA/COC
    if cert_type in ("COCA", "COC"):
        cert_extra["compliance_statement"] = cert_data.get("compliance_statement", "")
    cert_json = json.dumps(cert_extra, indent=2)

    extra_map = {"COA": EXTRA_COA, "COCA": EXTRA_COCA, "COC": EXTRA_COC}
    extra = extra_map.get(cert_type, EXTRA_COA)

    prompt = AI_COMPARISON_PROMPT.format(
        spec_json=spec_json,
        cert_json=cert_json,
        cert_type=cert_type,
        extra_instructions=extra,
    )

    response = client.chat.completions.create(
        model=model,
        temperature=config.TEMPERATURE,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    result_text = response.choices[0].message.content.strip()

    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        return {"product_match": True, "parameters": [], "error": result_text[:200]}


# ─── Legacy name-based matching (fallback) ────────────────────────────

def _match_parameters_legacy(spec_params: List[Dict], cert_params: List[Dict]) -> List[Dict]:
    """
    Fallback: Match spec parameters to certificate parameters by name.
    Priority: exact name match → normalized name match.
    """
    cert_by_name = {}
    cert_by_norm = {}
    for p in cert_params:
        cert_by_name[p.get("name", "").strip()] = p
        cert_by_norm[normalize_param_name(p.get("name", ""))] = p

    results = []
    for spec_param in spec_params:
        spec_name = spec_param.get("name", "").strip()
        spec_norm = normalize_param_name(spec_name)
        cert_param = cert_by_name.get(spec_name) or cert_by_norm.get(spec_norm)

        if cert_param is None:
            results.append({
                "parameter": spec_name,
                "spec_value": spec_param.get("value", ""),
                "spec_min": spec_param.get("min_limit", ""),
                "spec_max": spec_param.get("max_limit", ""),
                "cert_value": "",
                "cert_unit": "",
                "status": "REVIEW",
                "reason": f"Missing parameter in certificate: {spec_name}",
            })
        else:
            results.append(_compare_single_param(spec_param, cert_param))
    return results


def _compare_single_param(spec_param: Dict, cert_param: Dict) -> Dict:
    """Compare a single spec parameter against its certificate counterpart."""
    spec_name = spec_param.get("name", "").strip()
    spec_unit = spec_param.get("unit", "")
    cert_unit = cert_param.get("unit", "")
    spec_min_str = spec_param.get("min_limit", "")
    spec_max_str = spec_param.get("max_limit", "")
    cert_value_str = cert_param.get("value", "")
    spec_value_str = spec_param.get("value", "")

    result = {
        "parameter": spec_name,
        "spec_value": spec_value_str,
        "spec_min": spec_min_str,
        "spec_max": spec_max_str,
        "spec_unit": spec_unit,
        "cert_value": cert_value_str,
        "cert_unit": cert_unit,
        "status": "PASS",
        "reason": "",
    }

    cert_val, cert_qualifier = parse_value(cert_value_str)

    if cert_qualifier == "qualitative":
        if spec_min_str or spec_max_str:
            result["status"] = "REVIEW"
            result["reason"] = f"Qualitative cert value '{cert_value_str}' vs numeric spec limits"
        else:
            spec_val_norm = normalize_param_name(spec_value_str)
            cert_val_norm = normalize_param_name(cert_value_str)
            if spec_val_norm and cert_val_norm and spec_val_norm != cert_val_norm:
                result["status"] = "REVIEW"
                result["reason"] = f"Qualitative mismatch: spec='{spec_value_str}' vs cert='{cert_value_str}'"
        return result

    if cert_qualifier == "not_detected":
        if spec_max_str:
            result["status"] = "PASS"
            result["reason"] = "Not detected — within max limit"
        else:
            result["status"] = "REVIEW"
            result["reason"] = "Not detected — no spec limit to validate against"
        return result

    if cert_val is None:
        result["status"] = "REVIEW"
        result["reason"] = f"Cannot parse certificate value: '{cert_value_str}'"
        return result

    if not spec_min_str and not spec_max_str:
        result["status"] = "REVIEW"
        result["reason"] = "No numeric spec limits to compare against"
        return result

    actual_value = cert_val
    if spec_unit and cert_unit and normalize_unit(spec_unit) != normalize_unit(cert_unit):
        if are_units_compatible(spec_unit, cert_unit):
            converted = convert_value(cert_val, cert_unit, spec_unit)
            if converted is not None:
                actual_value = converted
            else:
                result["status"] = "REVIEW"
                result["reason"] = f"Unit conversion failed: {cert_unit} → {spec_unit}"
                return result
        else:
            result["status"] = "REVIEW"
            result["reason"] = f"Incompatible units: spec={spec_unit}, cert={cert_unit}"
            return result

    try:
        if spec_min_str:
            min_val, _ = parse_value(spec_min_str)
            if min_val is not None and actual_value < min_val:
                result["status"] = "FAIL"
                result["reason"] = f"{spec_name}: {actual_value} below minimum {min_val}"
                return result

        if spec_max_str:
            max_val, _ = parse_value(spec_max_str)
            if max_val is not None and actual_value > max_val:
                result["status"] = "FAIL"
                result["reason"] = f"{spec_name}: {actual_value} exceeds maximum {max_val}"
                return result

        if cert_qualifier == "less_than" and spec_max_str:
            max_val, _ = parse_value(spec_max_str)
            if max_val is not None and cert_val <= max_val:
                result["status"] = "PASS"
                result["reason"] = f"Value <{cert_val} within max limit {max_val}"
                return result

    except (ValueError, TypeError) as e:
        result["status"] = "REVIEW"
        result["reason"] = f"Comparison error: {str(e)}"
        return result

    return result


# ═══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

def compare_documents(
    spec_data: Dict,
    cert_data: Dict,
    cert_type: str = "COA",
    model: str = None,
) -> Dict:
    """
    Compare extracted spec data against certificate data.

    Uses AI-powered comparison for ALL certificate types (COA, COCA, COC).
    Handles parameter name differences, product mismatch detection,
    compliance statements, and numeric/qualitative validation.

    Args:
        spec_data: Extracted spec JSON
        cert_data: Extracted certificate JSON
        cert_type: Type of certificate (COA, COCA, COC)
        model: OpenAI model override

    Returns:
        dict with overall status, reason, and parameter details
    """

    # ── Step 0: Product mismatch pre-check ──
    spec_product = spec_data.get("product_name", "")
    cert_product = cert_data.get("product_name", "")
    is_match, match_conf, match_reason = _check_product_match(spec_product, cert_product)

    if not is_match:
        return {
            "status": "FAIL",
            "reason": match_reason,
            "cert_type": cert_type,
            "product_name": spec_product,
            "cert_product_name": cert_product,
            "batch_number": cert_data.get("batch_number", ""),
            "product_mismatch": True,
            "parameters_checked": 0,
            "parameters_passed": 0,
            "parameters_failed": 0,
            "parameters_review": 0,
            "details": [],
        }

    # ── Check what data we have ──
    spec_params = spec_data.get("parameters", [])
    cert_params = cert_data.get("parameters", [])
    compliance = cert_data.get("compliance_statement", "")

    if not spec_params:
        return {
            "status": "REVIEW",
            "reason": "No parameters found in specification",
            "cert_type": cert_type,
            "product_name": spec_product,
            "batch_number": cert_data.get("batch_number", ""),
            "parameters_checked": 0,
            "parameters_passed": 0,
            "parameters_failed": 0,
            "parameters_review": 1,
            "details": [],
        }

    # For COCA/COC with NO test data, fall back to compliance statement check
    if cert_type in ("COCA", "COC") and not cert_params:
        if compliance:
            return {
                "status": "PASS",
                "reason": f"Compliance statement present (no test data to compare): {compliance[:150]}",
                "cert_type": cert_type,
                "product_name": cert_product or spec_product,
                "batch_number": cert_data.get("batch_number", ""),
                "compliance_statement": compliance,
                "parameters_checked": 0,
                "parameters_passed": 0,
                "parameters_failed": 0,
                "parameters_review": 0,
                "details": [],
            }
        else:
            return {
                "status": "REVIEW",
                "reason": "No compliance statement and no test data found in certificate",
                "cert_type": cert_type,
                "product_name": cert_product or spec_product,
                "batch_number": cert_data.get("batch_number", ""),
                "parameters_checked": 0,
                "parameters_passed": 0,
                "parameters_failed": 0,
                "parameters_review": 1,
                "details": [],
            }

    # For COA with no cert params
    if cert_type == "COA" and not cert_params:
        return {
            "status": "REVIEW",
            "reason": "No parameters found in certificate",
            "cert_type": cert_type,
            "product_name": cert_product or spec_product,
            "batch_number": cert_data.get("batch_number", ""),
            "parameters_checked": 0,
            "parameters_passed": 0,
            "parameters_failed": 0,
            "parameters_review": 1,
            "details": [],
        }

    # ── AI-powered intelligent comparison (ALL cert types) ──
    try:
        ai_result = _ai_compare(spec_data, cert_data, cert_type=cert_type, model=model)
    except Exception:
        # Fallback to legacy matching if AI call fails
        ai_result = None

    if ai_result and ai_result.get("parameters"):
        # AI detected product mismatch
        if ai_result.get("product_match") is False:
            return {
                "status": "FAIL",
                "reason": ai_result.get("product_match_reason",
                    f"Product mismatch: spec='{spec_product}' vs cert='{cert_product}'"),
                "cert_type": cert_type,
                "product_name": spec_product,
                "cert_product_name": cert_product,
                "batch_number": cert_data.get("batch_number", ""),
                "product_mismatch": True,
                "parameters_checked": 0,
                "parameters_passed": 0,
                "parameters_failed": 0,
                "parameters_review": 0,
                "details": [],
            }

        # Build details from AI alignment
        details = []
        for p in ai_result["parameters"]:
            details.append({
                "parameter": p.get("spec_parameter", ""),
                "cert_parameter": p.get("cert_parameter", ""),
                "spec_value": p.get("spec_value", ""),
                "spec_min": p.get("spec_min", ""),
                "spec_max": p.get("spec_max", ""),
                "spec_unit": p.get("spec_unit", ""),
                "cert_value": p.get("cert_value", ""),
                "cert_unit": p.get("cert_unit", ""),
                "status": p.get("status", "REVIEW"),
                "reason": p.get("reason", ""),
            })

        # Include compliance info for COCA/COC
        ai_compliance = ai_result.get("compliance_statement", "") or compliance
    else:
        # Fallback to legacy name-based matching
        details = _match_parameters_legacy(spec_params, cert_params)
        ai_compliance = compliance

    # ── Determine overall status ──
    # Separate matched parameters (PASS/FAIL/REVIEW) from NOT_IN_CERT
    statuses = [d["status"] for d in details]
    matched_statuses = [s for s in statuses if s != "NOT_IN_CERT"]
    not_in_cert_count = statuses.count("NOT_IN_CERT")

    if "FAIL" in matched_statuses:
        overall_status = "FAIL"
    elif "REVIEW" in matched_statuses:
        overall_status = "REVIEW"
    elif matched_statuses:
        # All matched parameters PASS — overall PASS
        overall_status = "PASS"
    elif not_in_cert_count > 0:
        # No matched parameters at all, everything NOT_IN_CERT
        overall_status = "REVIEW"
    else:
        overall_status = "REVIEW"

    fail_reasons = [d["reason"] for d in details if d["status"] == "FAIL"]
    review_reasons = [d["reason"] for d in details if d["status"] == "REVIEW"]
    not_in_cert_reasons = [d["parameter"] for d in details if d["status"] == "NOT_IN_CERT"]
    all_reasons = fail_reasons + review_reasons
    if not_in_cert_reasons:
        all_reasons.append(f"Not in cert: {', '.join(not_in_cert_reasons)}")

    result = {
        "status": overall_status,
        "reason": "; ".join(all_reasons) if all_reasons else "All parameters within specification",
        "cert_type": cert_type,
        "product_name": spec_product or cert_product,
        "batch_number": cert_data.get("batch_number", ""),
        "parameters_checked": len(details),
        "parameters_passed": statuses.count("PASS"),
        "parameters_failed": statuses.count("FAIL"),
        "parameters_review": statuses.count("REVIEW"),
        "parameters_not_in_cert": not_in_cert_count,
        "details": details,
    }

    # Add compliance statement info for COCA/COC
    if cert_type in ("COCA", "COC") and ai_compliance:
        result["compliance_statement"] = ai_compliance

    return result
