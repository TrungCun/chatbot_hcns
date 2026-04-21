from typing import Literal, Optional
from typing_extensions import TypedDict


class AppState(TypedDict):
    """
    State của Parent Graph.

    Nguyên tắc:
      - Chỉ chứa các field mà Parent Graph CẦN ĐỌC.
      - Subgraph kế thừa AppState và thêm các field nội bộ riêng.
      - Sau khi subgraph chạy xong, chỉ các field có trong AppState
        được merge trở về parent — field nội bộ của subgraph bị giữ lại.

    Khi thêm subgraph mới:
      - Tạo SubgraphState(AppState) trong file state riêng của subgraph đó.
      - Không cần sửa AppState.
    """

    # --- Input ---
    message: str                                         # tin nhắn hiện tại từ user

    # --- Routing ---
    intent: Literal["ask", "provide"]                    # output của classify_intent
    current_phase: Literal["conversation", "interview"]  # phase hiện tại của session

    # --- Output ---
    response: Optional[str]                              # câu trả lời cuối cùng → trả về user
