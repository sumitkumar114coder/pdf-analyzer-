import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import pytesseract, set to None if missing
try:
    import pytesseract
except ImportError:
    pytesseract = None

def extract_ocr_from_page(img_bytes: bytes) -> str:
    """
    Runs Tesseract OCR on page image bytes.
    Fails gracefully if pytesseract or system tesseract binary is missing.
    """
    if pytesseract is None:
        logger.warning("pytesseract Python library is not installed. Skipping OCR fallback.")
        return ""

    try:
        # Open image from in-memory PNG bytes
        image = Image.open(io.BytesIO(img_bytes))
        
        # Run OCR string extraction
        ocr_text = pytesseract.image_to_string(image)
        return ocr_text
    except Exception as e:
        logger.error(f"OCR extraction failed (check if Tesseract-OCR binary is on PATH): {e}")
        return ""
