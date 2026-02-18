"""
Certificate Extractor — Extracts structured data from COA / COCA / COC PDFs.

Uses GPT-4o Vision to read certificate documents and extract measured values,
batch information, and compliance statements.
"""

import json
from pathlib import Path
from openai import OpenAI
from pydantic import ValidationError

import config
from core.pdf_renderer import pdf_to_base64_images
from core.retry_config import retry_openai_call, retry_file_io
from core.schemas import CertificateSchema

client = OpenAI(api_key=config.OPENAI_API_KEY)

COA_EXTRACTION_PROMPT = """You are an expert chemical certificate analyst.

Analyze this Certificate of Analysis (COA) document and extract ALL test results and batch information.

IMPORTANT RULES:
1. Extract EVERY test parameter shown — do not skip any.
2. Use STANDARDIZED parameter names where possible:
   - For concentration/strength: use "Strength" or "Assay" or "Concentration" (include the chemical name)
   - For specific gravity/density: use "Specific Gravity" or "Density" or "SG"
   - For appearance: use "Appearance"
   - For pH: use "pH"
   - For heavy metals: use common name ("Lead", "Arsenic", "Mercury", "Iron", "Copper", "Cadmium")
   - For residues: use "Non-Volatile Residue" or "Residue on Ignition"
3. Extract ALL numeric values with their units.
4. If the cert shows specification limits alongside results, include them in min_limit/max_limit.
5. If a result says "Pass", "Conforms", "Complies" — put that in value.
6. If a result says "ND", "Not Detected", "BDL" — put "ND" in value.
7. Extract batch/lot number, dates, product name.

Return ONLY valid JSON in this EXACT format:
{
  "document_type": "COA",
  "product_name": "<full product name>",
  "batch_number": "<batch or lot number>",
  "date_of_manufacture": "<date if found, else empty string>",
  "expiry_date": "<expiry date if found, else empty string>",
  "supplier_name": "<supplier/manufacturer name if found, else empty string>",
  "confidence_score": <float 0.0-1.0>,
  "parameters": [
    {
      "name": "<parameter name>",
      "value": "<measured/actual value>",
      "unit": "<unit of measurement>",
      "min_limit": "<min limit if shown on cert, else empty string>",
      "max_limit": "<max limit if shown on cert, else empty string>"
    }
  ]
}

Extract ALL parameters. Do not skip any test results shown in the document.
"""

COCA_COC_EXTRACTION_PROMPT = """You are an expert chemical certificate analyst.

Analyze this Certificate of Compliance / Conformance document and extract ALL information.

IMPORTANT: COCA and COC certificates often contain BOTH:
- A compliance statement AND actual test data/parameters.
- Extract EVERYTHING — do not treat compliance statement as the only content.

Extract:
1. Product name, batch/lot number, dates
2. ANY compliance statements or declarations (full text)
3. ALL parameters listed with their values — even if shown as specification ranges
4. If the cert shows spec ranges (e.g., "7.90 - 8.20"), extract them as ranges
5. Certifying authority / signatory information
6. Reference specification or standard
7. Supplier/manufacturer name

For parameters:
- If a specific tested value is shown, put it in "value"
- If only a specification range is shown (not a tested value), put the range as "value"
  and also populate min_limit and max_limit
- If result is "Pass", "Conforms", "Complies" — put that in value

Return ONLY valid JSON in this EXACT format:
{
  "document_type": "<COCA or COC>",
  "product_name": "<full product name>",
  "batch_number": "<batch or lot number>",
  "date_of_manufacture": "<date if found, else empty string>",
  "expiry_date": "<expiry date if found, else empty string>",
  "compliance_statement": "<full compliance declaration text>",
  "certifying_authority": "<name/org of certifier>",
  "reference_standard": "<referenced spec or standard>",
  "supplier_name": "<supplier/manufacturer name if found, else empty string>",
  "confidence_score": <float 0.0-1.0>,
  "parameters": [
    {
      "name": "<parameter name>",
      "value": "<value or compliance status>",
      "unit": "<unit if applicable>",
      "min_limit": "<min limit if shown>",
      "max_limit": "<max limit if shown>"
    }
  ]
}

Extract ALL parameters AND the compliance statement. Do not skip anything.
"""


def extract_certificate(pdf_path: str, model: str = None, expected_type: str = "COA") -> dict:
    """
    Extract structured data from a certificate PDF (COA, COCA, or COC).

    Args:
        pdf_path: Path to the certificate PDF
        model: OpenAI model to use
        expected_type: Expected certificate type ("COA", "COCA", "COC")

    Returns:
        dict with product info, batch info, and parameters
    """
    model = model or config.DEFAULT_MODEL
    pdf_path = str(Path(pdf_path).resolve())

    images_b64 = pdf_to_base64_images(pdf_path)

    # Choose prompt based on expected type
    if expected_type == "COA":
        prompt = COA_EXTRACTION_PROMPT
    else:
        prompt = COCA_COC_EXTRACTION_PROMPT

    # Build message content with all pages
    content = [{"type": "text", "text": prompt}]
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high",
            },
        })

    @retry_openai_call
    def _call_openai():
        return client.chat.completions.create(
            model=model,
            temperature=config.TEMPERATURE,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
        )
    
    response = _call_openai()
    result_text = response.choices[0].message.content.strip()

    try:
        result_dict = json.loads(result_text)
    except json.JSONDecodeError:
        result_dict = {
            "document_type": expected_type,
            "product_name": "",
            "batch_number": "",
            "confidence_score": 0.0,
            "parameters": [],
            "error": f"Failed to parse: {result_text[:200]}",
        }

    # Validate with Pydantic schema
    try:
        validated = CertificateSchema(**result_dict)
        result = validated.model_dump()
    except ValidationError as e:
        # Log validation error but continue with best-effort result
        print(f"Schema validation warning in extract_certificate: {e}")
        # Ensure required fields exist
        result_dict.setdefault("document_type", expected_type)
        result_dict.setdefault("product_name", "")
        result_dict.setdefault("batch_number", "")
        result_dict.setdefault("confidence_score", 0.0)
        result_dict.setdefault("parameters", [])
        result = result_dict

    # Save extracted JSON
    output_name = Path(pdf_path).stem + f"_{expected_type.lower()}.json"
    output_path = config.JSON_OUTPUT_DIR / output_name
    
    @retry_file_io
    def _save_json():
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
    _save_json()

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cert_type = sys.argv[2] if len(sys.argv) > 2 else "COA"
        result = extract_certificate(sys.argv[1], expected_type=cert_type)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python cert_extractor.py <path_to_cert_pdf> [COA|COCA|COC]")
