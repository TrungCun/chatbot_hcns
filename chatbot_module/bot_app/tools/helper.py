import os
import heapq
import io
import re
import time
import base64
import traceback
import docx
import pytesseract
import fitz
import asyncio
from PIL import Image
from typing import Any, Dict, List, Optional
from qdrant_client.models import QueryResponse
from bot_app.tools.embed import EmbedTools
from bot_app.tools.qdrant import QdrantTools
from bot_app.config import settings
from bot_app.schema.chat_schema import FilePayload

from bot_app.log import get_logger
logger = get_logger(__name__)

MAX_CHARS = 100_000

class HelperTools:
    @staticmethod
    def _save_file_sync(file_path: str, content: bytes):
        with open(file_path, "wb") as f:
            f.write(content)

    @staticmethod
    async def save_files_locally(files: List[FilePayload], user_id: str, session_id: str) -> List[str]:
        """
        Lưu danh sách file vào thư mục local theo cấu trúc: uploads/{user_id}/{session_id}/
        Trả về danh sách các đường dẫn (paths) của các file đã lưu.
        """
        if not files:
            return []

        # Tránh lỗi path traversal
        safe_user_id = re.sub(r'[^\w\.-]', '_', str(user_id))
        safe_session_id = re.sub(r'[^\w\.-]', '_', str(session_id))
        base_dir = os.path.join("chatbot_module", "uploads", safe_user_id, safe_session_id)

        try:
            os.makedirs(base_dir, exist_ok=True)
            saved_paths = []

            for file_payload in files:
                # Tránh các ký tự đặc biệt trong filename để an toàn cho filesystem
                safe_filename = re.sub(r'[^\w\.-]', '_', file_payload.filename)
                # Thêm timestamp vào filename để tránh trùng lặp
                timestamp = int(time.time())
                final_filename = f"{timestamp}_{safe_filename}"
                file_path = os.path.join(base_dir, final_filename)

                # Ghi file trong thread để không block Event Loop
                await asyncio.to_thread(HelperTools._save_file_sync, file_path, file_payload.content)

                saved_paths.append(file_path)
                logger.info(f"[HelperTools] Đã lưu file: {file_path}")

            return saved_paths

        except Exception as e:
            logger.error(f"[HelperTools] Lỗi khi lưu file: {str(e)}", exc_info=True)
            # Tạm thời trả về list trống nếu lỗi, không làm crash service
            return []

    @staticmethod
    def sanitize_n8n_value(value: Any) -> Any:
        """
        Sanitize 'undefined' string coercion from n8n / JS.
        """
        if isinstance(value, str) and value.strip().lower() == "undefined":
            return None
        return value

    @staticmethod
    def decode_n8n_base64(n8n_file_data: str) -> bytes:
        """
        Extract and decode base64 data from n8n binary format (handles Data URIs).
        """
        if "," in n8n_file_data and n8n_file_data.startswith("data:"):
            n8n_file_data = n8n_file_data.split(",", 1)[1]
        return base64.b64decode(n8n_file_data)

    @staticmethod
    def normalize_file(content: bytes, filename: str, content_type: str = None) -> Any:
        """
        Use filetype to guess MIME type and ensure filename has correct extension.
        Returns a dictionary or object compatible with FilePayload.
        """
        from bot_app.schema.chat_schema import FilePayload
        import filetype

        actual_filename = filename or "unknown_file"
        actual_content_type = content_type or "application/octet-stream"

        kind = filetype.guess(content)
        if kind is not None:
            actual_content_type = kind.mime
            extension = kind.extension
            if not actual_filename.lower().endswith(f".{extension}"):
                actual_filename = f"{actual_filename}.{extension}"

        return FilePayload(
            filename=actual_filename,
            content_type=actual_content_type,
            content=content
        )

    @staticmethod
    def reciprocal_rank_fusion(
        points: List["QueryResponse"] = None, n_points: int = None, k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combines dense and sparse retrieval results using Reciprocal Rank Fusion (RRF)
        and returns a list of dicts with {id, context}.
        """
        start_time = time.perf_counter()
        try:
            if not points or len(points) < 2:
                raise ValueError(
                    "Expected two sets of points: dense and sparse results."
                )

            dense_results = points[0].points
            sparse_results = points[1].points

            dense_scores = {str(r.id): r.score for r in dense_results}
            sparse_scores = {str(r.id): r.score for r in sparse_results}
            all_doc_ids = dense_scores.keys() | sparse_scores.keys()
            doc_lookup = {
                str(result.id): result for result in dense_results + sparse_results
            }

            dense_ranked = sorted(
                dense_scores.items(), key=lambda x: x[1], reverse=True
            )
            sparse_ranked = sorted(
                sparse_scores.items(), key=lambda x: x[1], reverse=True
            )
            dense_ranks = {
                doc_id: rank + 1 for rank, (doc_id, _) in enumerate(dense_ranked)
            }
            sparse_ranks = {
                doc_id: rank + 1 for rank, (doc_id, _) in enumerate(sparse_ranked)
            }

            rrf_scores = {
                doc_id: (1 / (k + dense_ranks.get(doc_id, len(dense_results) + 1)))
                + (1 / (k + sparse_ranks.get(doc_id, len(sparse_results) + 1)))
                for doc_id in all_doc_ids
            }

            if n_points and n_points < len(rrf_scores):
                top_doc_ids = [
                    doc_id
                    for doc_id, _ in heapq.nlargest(
                        n_points, rrf_scores.items(), key=lambda x: x[1]
                    )
                ]
            else:
                top_doc_ids = sorted(
                    rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
                )[:n_points]

            results = []
            for doc_id in top_doc_ids:
                doc = doc_lookup[doc_id]

                # Trả về cấu trúc core linh hoạt, không phụ thuộc vào metadata cụ thể
                result_item = {
                    "id": doc.id,
                    "score": rrf_scores[doc_id],
                    "payload": doc.payload,  # Giữ toàn bộ metadata để xử lý tùy biến ở tầng trên
                }
                results.append(result_item)

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"RRF fusion latency: {latency_ms:.2f} ms "
                f"(dense={len(dense_results)}, sparse={len(sparse_results)}, top={len(results)})"
            )
            # Log IDs để debug nhưng không làm rối log nếu kết quả lớn
            logger.info(f"Top {len(results)} RRF results: {[r['id'] for r in results[:5]]}...")
            return results

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"RRF fusion failed after {latency_ms:.2f} ms: {e}",
                exc_info=True,
            )
            traceback.print_exc()
            return [{"error": str(e)}]

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text by normalizing whitespace, removing noise, and fixing encoding issues."""
        if not text:
            return ""

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
        text = text.replace("–", "-").replace("—", "-")
        text = text.replace("“", '"').replace("”", '"').replace("’", "'")

        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n...[TRUNCATED]..."

        return text.strip()

    @staticmethod
    def clean_field_name(name: str) -> str:
        import re

        """Convert field names to safe Qdrant-compatible keys."""
        name = re.sub(
            r"[^\w]", "_", name.strip()
        )  # Replace spaces/symbols with underscores
        name = re.sub(r"_+", "_", name)  # Collapse multiple underscores
        return name.strip("_")

    @staticmethod
    def clean_text_for_payload(value) -> str:
        """Normalize text values for payload."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def flatten_field(value):
        if value is None:
            return None
        if isinstance(value, list):
            if not value:
                return None
            return "; ".join(map(str, value))
        if isinstance(value, str):
            if not value:
                return None
            return value.strip() or None
        return value

    @staticmethod
    def ensure_dict(data: Any) -> Dict[str, Any]:
        """
        Cơ chế ép kiểu tuyệt đối: Biến mọi input (Pydantic Object, JSON string, hoặc Dict)
        về đúng chuẩn Dictionary tĩnh để thao tác an toàn.
        """
        if not data:
            return {}

        # Nếu đã là dict thì trả về luôn
        if isinstance(data, dict):
            return data

        # Nếu là Pydantic V2
        if hasattr(data, "model_dump"):
            return data.model_dump()

        # Nếu là Pydantic V1 (dự phòng)
        if hasattr(data, "dict"):
            return data.dict()

        # Fallback cho các object Python thông thường
        if hasattr(data, "__dict__"):
            return vars(data)

        return {}

    @staticmethod
    def _extract_pdf_sync(file_content: bytes, filename: str, max_pages: int = 10) -> str:
        """
        Trích xuất Text từ PDF. Nếu không tìm thấy text (nghi là file scan),
        sẽ tự động fallback sang OCR từng trang bằng Tesseract.
        """
        text_parts = [f"--- Bắt đầu tài liệu: {filename} ---\n\n"]
        try:
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                total_pages = len(doc)
                pages_to_read = min(total_pages, max_pages)

                if total_pages > max_pages:
                    logger.warning(f"[HELPER / PDF] File {filename} ({total_pages} trang) vượt giới hạn. Chỉ đọc {max_pages} trang.")

                native_text_found = False
                temp_parts = []

                # Bước 1: Thử trích xuất text có sẵn (Native Text)
                for i in range(pages_to_read):
                    page = doc[i]
                    page_text = page.get_text("text", sort=True).strip()
                    if page_text:
                        temp_parts.append(f"### [Trang {i+1}] ###\n{page_text}\n\n")
                        native_text_found = True

                # Bước 2: Nếu không thấy text nào (PDF Scan), thực hiện OCR từng trang
                if not native_text_found:
                    logger.info(f"[HELPER / PDF] File '{filename}' không có text. Đang thử chạy OCR (Tesseract)...")
                    temp_parts.append("[Nội dung trích xuất qua OCR do file là dạng ảnh quét]\n")

                    for i in range(pages_to_read):
                        page = doc[i]
                        # Render trang thành ảnh để OCR
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom 2x để tăng độ chính xác OCR
                        img = Image.open(io.BytesIO(pix.tobytes("png")))

                        ocr_text = pytesseract.image_to_string(img, lang='vie+eng').strip()
                        if ocr_text:
                            temp_parts.append(f"### [Trang {i+1} (OCR)] ###\n{ocr_text}\n\n")

                if not native_text_found and len(temp_parts) <= 1:
                    temp_parts.append("[Tài liệu không chứa văn bản có thể đọc được kể cả qua OCR]\n")

                text_parts.extend(temp_parts)

            logger.info(f"[HELPER / PDF] Đã trích xuất xong tài liệu '{filename}'.")
            return "".join(text_parts)

        except Exception as e:
            logger.error(f"[HELPER / PDF] Lỗi khi xử lý PDF {filename}: {e}")
            return f"--- Lỗi khi trích xuất nội dung file {filename}: {str(e)} ---"

    @staticmethod
    def _extract_image_sync(file_content: bytes) -> str:
        img = Image.open(io.BytesIO(file_content))
        return pytesseract.image_to_string(img, lang='vie+eng')

    @staticmethod
    def _extract_word_sync(file_content: bytes) -> str:
        doc = docx.Document(io.BytesIO(file_content))
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)

    @staticmethod
    async def process_files(files: List[FilePayload]) -> str:
        extracted_content = []

        for file in files:
            # Check type of file
            mime = file.content_type.lower()

            # --- CASE: PDF ---
            if mime == "application/pdf" or file.filename.lower().endswith(".pdf"):
                try:
                    # Gọi hàm xử lý PDF (có tích hợp OCR fallback) trong thread pool
                    content = await asyncio.to_thread(HelperTools._extract_pdf_sync, file.content, file.filename)
                    if content.strip():
                        extracted_content.append(content)
                        logger.info(f"[HELPER / PROCESS FILES] PDF file '{file.filename}' processed.")
                except Exception as e:
                    logger.error(f"[HELPER / PROCESS FILES] Error processing PDF '{file.filename}': {e}")

            # --- CASE: IMAGES (OCR via Tesseract) ---
            elif mime.startswith("image/"):
                try:
                    # Chạy OCR trong thread pool để không block Event Loop
                    text = await asyncio.to_thread(HelperTools._extract_image_sync, file.content)

                    if text.strip():
                        extracted_content.append(f"--- Nội dung trích xuất từ hình ảnh: {file.filename} ---\n{text}")
                        logger.info(f"[HELPER / PROCESS FILES] Image OCR success for '{file.filename}'.")
                except Exception as e:
                    logger.error(f"[HELPER / PROCESS FILES] OCR failed for '{file.filename}': {e}")

            # --- CASE: WORD (DOCX) ---
            elif "word" in mime or file.filename.lower().endswith((".doc", ".docx")):
                try:
                    # Xử lý Word trong thread pool
                    content = await asyncio.to_thread(HelperTools._extract_word_sync, file.content)
                    if content.strip():
                        extracted_content.append(f"--- Nội dung file Word: {file.filename} ---\n{content}")
                        logger.info(f"[HELPER / PROCESS FILES] Word file '{file.filename}' processed.")
                except Exception as e:
                    logger.error(f"[HELPER / PROCESS FILES] Failed to read Word file '{file.filename}': {e}")

            # Process text file or csv
            elif "text/" in mime or mime == "application/csv":
                try:
                    content =  file.content.decode("utf-8", errors="ignore")
                    if content.strip():
                        extracted_content.append(f"--- Nội dung file văn bản: {file.filename} ---\n{content}")
                        logger.info(f"[HELPER / PROCESS FILES] Text file '{file.filename}' processed.")
                except Exception as e:
                    logger.error(f"[HELPER / PROCESS FILES] Failed to read text file '{file.filename}': {e}")

            combined_text = "\n\n".join(extracted_content) if extracted_content else ""
            return combined_text
