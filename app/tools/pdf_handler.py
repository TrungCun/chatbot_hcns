import fitz  # PyMuPDF
import logging
from typing import List
from app.schema.chat_schema import Attachment

logger = logging.getLogger(__name__)

def process_pdf_to_text(file_content: bytes, filename: str) -> str:
    """
    Trích xuất text thuần từ file PDF.
    """
    text_content = ""
    try:
        # Mở PDF từ bytes
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            text_content += f"--- Nội dung file PDF: {filename} ---\n"
            for i in range(len(doc)):
                page = doc[i]
                page_text = page.get_text()
                text_content += f"[Trang {i+1}]\n{page_text}\n"

            logger.info(f"Extracted text from PDF '{filename}' ({len(doc)} pages).")
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filename}: {str(e)}")
        text_content = f"\n[Lỗi khi đọc file PDF {filename}]\n"

    return text_content
