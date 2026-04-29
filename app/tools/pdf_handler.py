import asyncio
import fitz

from app.log import get_logger
logger = get_logger(__name__)

def _extract_text_sync(file_content: bytes, filename: str, max_pages: int = 20) -> str:

    text_content = f"--- Bắt đầu tài liệu: {filename} ---\n\n"
    try:
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            total_pages = len(doc)

            if total_pages > max_pages:
                logger.warning(f"File {filename} ({total_pages} trang) vượt quá giới hạn. Chỉ đọc {max_pages} trang.")
                pages_to_read = max_pages
            else:
                pages_to_read = total_pages

            for i in range(pages_to_read):
                page = doc[i]

                page_text = page.get_text("text", sort=True)

                text_content += f"### [Trang {i+1}] ###\n{page_text.strip()}\n\n"

        logger.info(f"Đã trích xuất thành công {pages_to_read}/{total_pages} trang từ '{filename}'.")
        return text_content

    except fitz.FileDataError:
        logger.error(f"File PDF bị hỏng hoặc có mật khẩu bảo vệ: {filename}")
        raise ValueError(f"Không thể đọc file '{filename}'. File có thể bị hỏng hoặc yêu cầu mật khẩu.")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi trích xuất PDF {filename}: {e}", exc_info=True)
        raise RuntimeError(f"Lỗi hệ thống khi xử lý tài liệu '{filename}'.")


async def process_pdf_to_text(file_content: bytes, filename: str) -> str:
    return await asyncio.to_thread(_extract_text_sync, file_content, filename)