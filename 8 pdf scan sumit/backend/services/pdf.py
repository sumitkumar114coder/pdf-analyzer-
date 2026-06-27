import os
import logging
import fitz  # PyMuPDF

from backend.services.ocr import extract_ocr_from_page

logger = logging.getLogger(__name__)

def extract_pdf_content(file_path: str, use_ocr_fallback: bool = True) -> list[dict]:
    """
    Extracts text page-by-page from a PDF using PyMuPDF.
    If the text is too sparse, falls back to Tesseract OCR.
    """
    results = []

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Error opening PDF with PyMuPDF: {e}")
        raise ValueError(f"Could not parse the PDF structure: {str(e)}")

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        # Extract native layout text
        text = page.get_text().strip()
        is_ocr = False

        # If text is very short (< 50 chars), it is likely a scanned page or image
        if len(text) < 50 and use_ocr_fallback:
            logger.info(f"Page {page_num} of {file_path} has sparse text. Attempting OCR fallback...")
            try:
                # Render page at 150 DPI for reasonable OCR accuracy and speed
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                
                # Extract text using OCR
                ocr_text = extract_ocr_from_page(img_bytes)
                if ocr_text and len(ocr_text.strip()) > len(text):
                    text = ocr_text.strip()
                    is_ocr = True
                    logger.info(f"OCR successfully extracted {len(text)} characters for page {page_num}.")
            except Exception as ocr_err:
                logger.error(f"Failed to render/OCR page {page_num}: {ocr_err}")

        results.append({
            "page_number": page_num,
            "text": text,
            "is_ocr": is_ocr
        })

    doc.close()
    return results
