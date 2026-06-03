import os
from dotenv import load_dotenv
load_dotenv()

from bot_app.config import settings
os.environ["CUDA_VISIBLE_DEVICES"] = str(settings.gpu_device)

import asyncio
import threading
from typing import Optional, List

# Import các thành phần core của hệ thống Chatbot
from bot_app.application import application
from bot_app.tools.redis import init_redis
from bot_app.tools.mysql import init_mysql
from bot_app.schema.chat_schema import ChatRequest
from bot_app.services.chat_services import get_chat_service

_chatbot_loop = None
_thread = None

def _start_background_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def init_chatbot():
    """
    HÀM KHỞI TẠO HỆ THỐNG AI
    Đồng nghiệp chỉ cần import và gọi hàm này MỘT LẦN lúc khởi động app (trong main.py).
    Hàm sẽ tự động load model và kết nối database.
    """
    global _chatbot_loop, _thread
    
    if _chatbot_loop is not None:
        return
        
    print("[Chatbot Interface] Đang khởi tạo hệ thống AI...")
    
    # 1. Khởi tạo các module đồng bộ
    application.load_models()
    init_mysql()
    
    # 2. Tạo một Event Loop chạy ngầm để xử lý các hàm Async (bất đồng bộ) của Chatbot
    _chatbot_loop = asyncio.new_event_loop()
    _thread = threading.Thread(target=_start_background_loop, args=(_chatbot_loop,), daemon=True)
    _thread.start()
    
    # 3. Khởi tạo kết nối Redis trên Loop chạy ngầm
    asyncio.run_coroutine_threadsafe(init_redis(), _chatbot_loop).result()
    print("[Chatbot Interface] Hệ thống AI đã sẵn sàng!")


def get_chatbot_response(
    user_id: str,
    session_id: str,
    message: str,
    user_info: Optional[str] = None,
    job_context: Optional[str] = None,
    files: Optional[List] = None,
    timeout: int = 90,
) -> str:
    """
    HÀM LẤY CÂU TRẢ LỜI TỪ AI
    Đồng nghiệp gọi hàm này mỗi khi user nhắn tin tới. Hàm này chạy đồng bộ (Sync) 
    để tương thích hoàn toàn với Flask.
    """
    if _chatbot_loop is None:
        raise RuntimeError("Chatbot chưa được khởi tạo! Hãy gọi init_chatbot() trước.")
        
    # Đóng gói dữ liệu thành chuẩn của bạn
    request = ChatRequest(
        user_id=user_id,
        session_id=session_id,
        user_info=user_info,
        job_context=job_context,
        message=message,
        files=files or [],
    )
    
    service = get_chat_service()
    
    # Gửi Request vào background loop của Chatbot và đợi kết quả
    future = asyncio.run_coroutine_threadsafe(
        service.process_message(request), 
        _chatbot_loop
    )
    
    try:
        # Chờ tối đa "timeout" giây để AI sinh xong câu trả lời
        response_obj = future.result(timeout=timeout)
        return response_obj.response
    except Exception as e:
        print(f"[Chatbot Interface] Lỗi trong quá trình AI xử lý: {e}")
        return "Xin lỗi, hệ thống AI đang gặp sự cố. Vui lòng thử lại sau."
