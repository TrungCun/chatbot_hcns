from typing import List, Optional, Any
from langchain_core.messages import HumanMessage
from app.schema.chat_schema import Attachment

def get_multimodal_messages(message: str, attachments: Optional[List[Attachment]] = None) -> List[HumanMessage]:
    """
    Chuyển đổi message và attachments thành danh sách HumanMessage hỗ trợ Multimodal cho LangChain.
    """
    if not attachments:
        return [HumanMessage(content=message)]

    # Format chuẩn cho Vision models
    content = []

    # 1. Text content luôn đặt lên đầu
    content.append({"type": "text", "text": message})

    # 2. Thêm ảnh với chế độ detail='low' để tăng tốc độ xử lý
    for att in attachments:
        if att.content_type.startswith("image/"):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{att.content_type};base64,{att.content}",
                    "detail": "low"
                }
            })
        else:
            content.append({
                "type": "text",
                "text": f"\n[File đính kèm: {att.filename} ({att.content_type})]"
            })

    return [HumanMessage(content=content)]
