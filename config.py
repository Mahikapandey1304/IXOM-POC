"""
Configuration module for Intelligent Safety Net.
Loads environment variables and defines project-wide constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.resolve()
load_dotenv(PROJECT_ROOT / ".env")

# ─── API Configuration ───────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

# ─── Model Rankings ──────────────────────────────────────────────────
AVAILABLE_MODELS = [
    "gpt-4o",           # Best multimodal + reasoning
    "gpt-4.1",          # Latest iteration
    "gpt-4o-mini",      # Cost-effective batch
    "gpt-4-turbo",      # Fallback
]

# ─── Paths ────────────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
SPECS_DIR = DATA_DIR / "specs"
CERTS_DIR = DATA_DIR / "certificates"
MAPPING_FILE = DATA_DIR / "mapping.xlsx"

LOGS_DIR = PROJECT_ROOT / os.getenv("LOGS_DIR", "logs")
AUDIT_LOG = LOGS_DIR / "audit_log.csv"

OUTPUTS_DIR = PROJECT_ROOT / os.getenv("OUTPUTS_DIR", "outputs")
JSON_OUTPUT_DIR = OUTPUTS_DIR / "structured_json"

# Source PDFs folder (same directory as project)
SOURCE_PDFS_DIR = PROJECT_ROOT / "pdfs"

# ─── Extraction Settings ─────────────────────────────────────────────
MAX_PAGES_PER_DOC = 10          # Max pages to send to Vision API
IMAGE_DPI = 200                  # DPI for PDF-to-image conversion
MAX_IMAGE_SIZE = (2048, 2048)    # Max image dimensions for API

# ─── Certificate Types ───────────────────────────────────────────────
CERT_TYPES = ["COA", "COCA", "COC"]

# ─── Golden Test Rows (1-indexed S.N from mapping) ───────────────────
GOLDEN_TEST_ROWS = [1, 6, 11]   # One per industry: Food, Health, Water

# ─── Ensure directories exist ────────────────────────────────────────
for d in [SPECS_DIR, CERTS_DIR, LOGS_DIR, JSON_OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
