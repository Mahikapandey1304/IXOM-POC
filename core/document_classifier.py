"""
Document Classifier — Uses GPT-4o Vision to classify a PDF as:
  Product_Specification | COA | COCA | COC | Invoice | Other

Returns dict with document_type and confidence_score.
"""

import json
from pathlib import Path
from openai import OpenAI

import config
from core.pdf_renderer import pdf_page_to_base64

client = OpenAI(api_key=config.OPENAI_API_KEY)

CLASSIFICATION_PROMPT = """You are a document classification expert for industrial chemical products.

Analyze this document image and classify it as ONE of the following types:
- Product_Specification: A product specification sheet listing parameters, limits, and requirements
- COA: Certificate of Analysis — a lab test report with measured values for a batch
- COCA: Certificate of Compliance/Analysis — a compliance attestation with or without test data
- COC: Certificate of Conformance — a statement certifying product meets specifications
- Invoice: A commercial invoice or purchase order
- Other: Any document that does not fit the above categories

Return ONLY valid JSON in this exact format:
{
  "document_type": "<one of the types above>",
  "confidence_score": <float between 0.0 and 1.0>,
  "product_name": "<product name if identifiable, else empty string>",
  "reasoning": "<brief one-line explanation>"
}
"""


def classify_document(pdf_path: str, model: str = None) -> dict:
    """
    Classify a PDF document using GPT-4o Vision.

    Args:
        pdf_path: Path to the PDF file
        model: OpenAI model to use (defaults to config.DEFAULT_MODEL)

    Returns:
        dict with document_type, confidence_score, product_name, reasoning
    """
    model = model or config.DEFAULT_MODEL
    pdf_path = str(Path(pdf_path).resolve())

    # Convert first page to image
    img_b64 = pdf_page_to_base64(pdf_path, page_num=0)

    response = client.chat.completions.create(
        model=model,
        temperature=config.TEMPERATURE,
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CLASSIFICATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
    )

    result_text = response.choices[0].message.content.strip()

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        result = {
            "document_type": "Other",
            "confidence_score": 0.0,
            "product_name": "",
            "reasoning": f"Failed to parse response: {result_text[:200]}",
        }

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = classify_document(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python document_classifier.py <path_to_pdf>")
