"""
Spec Extractor — Extracts structured parameter data from Product Specification PDFs.

Uses GPT-4o Vision to read tables and extract parameters into the fixed JSON schema.
"""

import json
from pathlib import Path
from openai import OpenAI
from pydantic import ValidationError

import config
from core.pdf_renderer import pdf_to_base64_images
from core.retry_config import retry_openai_call, retry_file_io
from core.schemas import SpecificationSchema
from core.openai_helper import create_chat_completion

client = OpenAI(api_key=config.OPENAI_API_KEY)

SPEC_EXTRACTION_PROMPT = """You are an expert chemical product specification analyst.

Analyze ALL pages of this Product Specification document and extract EVERY parameter, limit, and requirement.

IMPORTANT RULES:
1. If the specification has MULTIPLE GRADES or PRODUCT VARIANTS in the same document,
   focus on the PRIMARY/MAIN grade (typically the one in the document title or listed first).
   Do NOT duplicate parameters from different grade tables.

2. If a parameter appears in multiple tables (e.g. different grades), extract the limits from
   the MAIN grade only — the one matching the product name.

3. Extract parameters exactly as shown — include:
   - Chemical assay / strength / purity / concentration
   - pH
   - Specific gravity / density
   - Heavy metals (Pb, As, Cd, Hg, Fe, Cu, etc.)
   - Impurities, residues, turbidity
   - Appearance, colour, odour (qualitative)
   - Foreign matter
   - Any other test parameters

4. For parameters with only a single limit:
   - "max" or "≤" or "<" → put value in max_limit, leave min_limit empty
   - "min" or "≥" or ">" → put value in min_limit, leave max_limit empty
   - Range "5.0 - 7.0" → put 5.0 in min_limit and 7.0 in max_limit

5. For qualitative parameters (Appearance: "Clear liquid"):
   - Put the expected description in "value"
   - Leave min_limit and max_limit empty

6. NEVER duplicate the same parameter. Each parameter should appear exactly ONCE.

Return ONLY valid JSON in this EXACT format:
{
  "document_type": "Product_Specification",
  "product_name": "<full product name from the document title>",
  "material_number": "<material/product code if found, else empty string>",
  "confidence_score": <float 0.0-1.0>,
  "parameters": [
    {
      "name": "<parameter name>",
      "value": "<typical or target value if given, else empty string>",
      "unit": "<unit of measurement>",
      "min_limit": "<minimum limit as string, or empty string>",
      "max_limit": "<maximum limit as string, or empty string>"
    }
  ]
}

Extract ALL parameters but do NOT duplicate any. Each unique parameter ONCE only.
"""


def extract_spec(pdf_path: str, model: str = None) -> dict:
    """
    Extract structured specification data from a Product Specification PDF.

    Args:
        pdf_path: Path to the spec PDF
        model: OpenAI model to use

    Returns:
        dict with product_name, material_number, parameters list
    """
    model = model or config.DEFAULT_MODEL
    pdf_path = str(Path(pdf_path).resolve())

    images_b64 = pdf_to_base64_images(pdf_path)

    # Build message content with all pages
    content = [{"type": "text", "text": SPEC_EXTRACTION_PROMPT}]
    for i, img_b64 in enumerate(images_b64):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high",
            },
        })

    response = create_chat_completion(
        client=client,
        model=model,
        temperature=config.TEMPERATURE,
        max_output_tokens=4096,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},
    )
    result_text = response.choices[0].message.content.strip()

    try:
        result_dict = json.loads(result_text)
    except json.JSONDecodeError:
        result_dict = {
            "document_type": "Product_Specification",
            "product_name": "",
            "material_number": "",
            "confidence_score": 0.0,
            "parameters": [],
            "error": f"Failed to parse: {result_text[:200]}",
        }

    # Validate with Pydantic schema
    try:
        validated = SpecificationSchema(**result_dict)
        result = validated.model_dump()
    except ValidationError as e:
        # Log validation error but continue with best-effort result
        print(f"Schema validation warning in extract_spec: {e}")
        # Ensure required fields exist
        result_dict.setdefault("document_type", "Product_Specification")
        result_dict.setdefault("product_name", "")
        result_dict.setdefault("material_number", "")
        result_dict.setdefault("confidence_score", 0.0)
        result_dict.setdefault("parameters", [])
        result = result_dict

    # Save extracted JSON
    output_name = Path(pdf_path).stem + "_spec.json"
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
        result = extract_spec(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python spec_extractor.py <path_to_spec_pdf>")
