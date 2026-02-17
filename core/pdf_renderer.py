"""
PDF Renderer — Converts PDF pages to base64-encoded PNG images using pypdfium2.

No external binary (Poppler) dependency required.
"""

import base64
import io
from pathlib import Path
from PIL import Image
import pypdfium2 as pdfium

import config


def pdf_page_to_base64(pdf_path: str, page_num: int = 0, dpi: int = None) -> str:
    """Convert a single PDF page to a base64-encoded PNG string."""
    dpi = dpi or config.IMAGE_DPI
    scale = dpi / 72  # pypdfium2 uses 72 DPI as base

    pdf = pdfium.PdfDocument(pdf_path)
    if page_num >= len(pdf):
        raise ValueError(f"Page {page_num} out of range (doc has {len(pdf)} pages)")

    page = pdf[page_num]
    bitmap = page.render(scale=scale)
    img = bitmap.to_pil()

    # Resize if too large
    if img.width > config.MAX_IMAGE_SIZE[0] or img.height > config.MAX_IMAGE_SIZE[1]:
        img.thumbnail(config.MAX_IMAGE_SIZE, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    pdf.close()
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def pdf_to_base64_images(pdf_path: str, dpi: int = None, max_pages: int = None) -> list:
    """Convert all pages of a PDF to base64-encoded PNG strings."""
    dpi = dpi or config.IMAGE_DPI
    max_pages = max_pages or config.MAX_PAGES_PER_DOC
    scale = dpi / 72

    pdf = pdfium.PdfDocument(pdf_path)
    n_pages = min(len(pdf), max_pages)

    result = []
    for i in range(n_pages):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil()

        if img.width > config.MAX_IMAGE_SIZE[0] or img.height > config.MAX_IMAGE_SIZE[1]:
            img.thumbnail(config.MAX_IMAGE_SIZE, Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    pdf.close()
    return result


def get_page_count(pdf_path: str) -> int:
    """Get the number of pages in a PDF."""
    pdf = pdfium.PdfDocument(pdf_path)
    count = len(pdf)
    pdf.close()
    return count
