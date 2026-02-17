"""
Unit Normalizer — Normalizes units and values for consistent comparison.

Handles common chemical/industrial unit conversions and value parsing.
"""

import re
from typing import Tuple, Optional

# ─── Unit Aliases → Canonical Form ────────────────────────────────────
UNIT_MAP = {
    # Concentration
    "%": "%",
    "% w/w": "%",
    "% w/v": "% w/v",
    "%w/w": "%",
    "%w/v": "% w/v",
    "percent": "%",
    "wt%": "%",
    "wt %": "%",
    "weight %": "%",
    "weight percent": "%",
    "vol%": "% v/v",
    "vol %": "% v/v",
    "% v/v": "% v/v",

    # Mass concentration
    "ppm": "ppm",
    "mg/l": "ppm",
    "mg/kg": "ppm",
    "µg/ml": "ppm",
    "ug/ml": "ppm",
    "ppb": "ppb",
    "µg/l": "ppb",
    "ug/l": "ppb",
    "µg/kg": "ppb",
    "g/l": "g/L",
    "g/ml": "g/mL",
    "mg/ml": "mg/mL",

    # pH
    "ph": "pH",
    "ph units": "pH",

    # Density / Specific Gravity
    "g/cm3": "g/cm³",
    "g/cm³": "g/cm³",
    "g/cc": "g/cm³",
    "kg/l": "kg/L",
    "kg/m3": "kg/m³",
    "kg/m³": "kg/m³",
    "sg": "SG",
    "specific gravity": "SG",

    # Temperature
    "°c": "°C",
    "degc": "°C",
    "deg c": "°C",
    "celsius": "°C",
    "°f": "°F",

    # General
    "ntu": "NTU",
    "hazen": "Hazen",
    "apha": "APHA",
    "meq/l": "meq/L",
    "ml": "mL",
    "l": "L",
    "mg": "mg",
    "g": "g",
    "kg": "kg",
}

# ─── Conversion factors to common base ────────────────────────────────
# Key: (from_unit, to_unit) → multiplier
CONVERSION_FACTORS = {
    ("mg/L", "ppm"): 1.0,
    ("ppm", "mg/L"): 1.0,
    ("mg/kg", "ppm"): 1.0,
    ("ppm", "mg/kg"): 1.0,
    ("µg/L", "ppb"): 1.0,
    ("ppb", "µg/L"): 1.0,
    ("g/L", "ppm"): 1000.0,
    ("ppm", "g/L"): 0.001,
    ("ppb", "ppm"): 0.001,
    ("ppm", "ppb"): 1000.0,
    ("g/cm³", "kg/L"): 1.0,
    ("kg/L", "g/cm³"): 1.0,
    ("mg/mL", "g/L"): 1.0,
    ("g/L", "mg/mL"): 1.0,
}


def normalize_unit(unit: str) -> str:
    """Normalize a unit string to its canonical form."""
    if not unit:
        return ""
    cleaned = unit.strip().lower()
    return UNIT_MAP.get(cleaned, unit.strip())


def parse_value(value_str: str) -> Tuple[Optional[float], str]:
    """
    Parse a value string into a float and any qualifier.

    Returns:
        (numeric_value, qualifier) where qualifier is one of:
        "", "less_than", "greater_than", "approximately", "not_detected"

    Examples:
        "5.2"       → (5.2, "")
        "<0.5"      → (0.5, "less_than")
        ">10"       → (10.0, "greater_than")
        "~3.0"      → (3.0, "approximately")
        "ND"        → (0.0, "not_detected")
        "N/A"       → (None, "not_applicable")
        "Conforms"  → (None, "qualitative")
    """
    if not value_str or not isinstance(value_str, str):
        return None, "empty"

    s = value_str.strip()

    # Not detected / below detection limit
    if s.upper() in ("ND", "N.D.", "BDL", "NOT DETECTED", "BELOW DETECTION LIMIT"):
        return 0.0, "not_detected"

    # Not applicable
    if s.upper() in ("N/A", "NA", "-", "—", ""):
        return None, "not_applicable"

    # Qualitative values (no numeric content)
    if not re.search(r'\d', s):
        return None, "qualitative"

    # Less than
    match = re.match(r'^[<≤]\s*([\d,]+\.?\d*)', s)
    if match:
        return float(match.group(1).replace(",", "")), "less_than"

    # Greater than
    match = re.match(r'^[>≥]\s*([\d,]+\.?\d*)', s)
    if match:
        return float(match.group(1).replace(",", "")), "greater_than"

    # Approximately
    match = re.match(r'^[~≈]\s*([\d,]+\.?\d*)', s)
    if match:
        return float(match.group(1).replace(",", "")), "approximately"

    # Plain number (possibly with commas)
    match = re.match(r'^([\d,]+\.?\d*)', s)
    if match:
        return float(match.group(1).replace(",", "")), ""

    return None, "unparseable"


def are_units_compatible(unit1: str, unit2: str) -> bool:
    """Check if two units can be meaningfully compared."""
    n1 = normalize_unit(unit1)
    n2 = normalize_unit(unit2)

    if n1 == n2:
        return True

    # Check if conversion exists
    return (n1, n2) in CONVERSION_FACTORS or (n2, n1) in CONVERSION_FACTORS


def convert_value(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert a value from one unit to another. Returns None if no conversion available."""
    n_from = normalize_unit(from_unit)
    n_to = normalize_unit(to_unit)

    if n_from == n_to:
        return value

    key = (n_from, n_to)
    if key in CONVERSION_FACTORS:
        return value * CONVERSION_FACTORS[key]

    return None


def normalize_param_name(name: str) -> str:
    """Normalize a parameter name for matching purposes."""
    if not name:
        return ""
    # Lowercase, strip whitespace, remove special chars
    s = name.strip().lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


if __name__ == "__main__":
    # Quick tests
    print(parse_value("<0.5"))      # (0.5, 'less_than')
    print(parse_value("99.8"))      # (99.8, '')
    print(parse_value("ND"))        # (0.0, 'not_detected')
    print(parse_value("Conforms"))  # (None, 'qualitative')
    print(normalize_unit("% w/w"))  # '%'
    print(normalize_unit("mg/L"))   # 'ppm'
