"""
Prompt Loader — load prompt từ file .md, cache in-memory.

Cách dùng trong node:
    from app.prompt.loader import load_prompt
    prompt = load_prompt("conversation/analyze_query")

Format file .md:
    - Dòng đầu có thể là comment (#...), bị bỏ qua
    - Phần còn lại là nội dung prompt
    - Dùng {variable} cho template variables (chuẩn LangChain)

Cache: prompt được load 1 lần, tái sử dụng cho các request tiếp theo.
Reload: restart server hoặc gọi clear_cache() khi cần hot-reload.
"""
from functools import lru_cache
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

_PROMPT_DIR = Path(__file__).parent
_COMMON_FILE = _PROMPT_DIR / "common.md"


def _load_common() -> str:
    """Đọc nội dung common.md nếu tồn tại, ngược lại trả về chuỗi rỗng."""
    if _COMMON_FILE.exists():
        return _COMMON_FILE.read_text(encoding="utf-8").strip() + "\n\n"
    return ""


@lru_cache(maxsize=64)
def load_prompt(name: str) -> ChatPromptTemplate:
    """
    Load prompt từ file app/prompt/{name}.md, tự động prepend common.md.

    Args:
        name: Đường dẫn tương đối không có extension.
              Ví dụ: "conversation/analyze_query", "parent/classify_intent"

    Returns:
        ChatPromptTemplate sẵn sàng dùng với | llm | StrOutputParser()

    Raises:
        FileNotFoundError: nếu file không tồn tại
    """
    path = _PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}\n"
            f"Expected at: app/prompt/{name}.md"
        )

    content = path.read_text(encoding="utf-8").strip()
    full_content = _load_common() + content
    return ChatPromptTemplate.from_template(full_content)


@lru_cache(maxsize=32)
def load_tool_description(name: str) -> str:
    """
    Load tool description từ file app/prompt/{name}.md — KHÔNG prepend common.md.
    Dùng cho @tool(description=...) trong LangChain.

    Args:
        name: Ví dụ: "tools/list_all_jobs"

    Returns:
        Chuỗi plain text dùng làm tool description.
    """
    path = _PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}\n"
            f"Expected at: app/prompt/{name}.md"
        )
    return path.read_text(encoding="utf-8").strip()


def clear_cache() -> None:
    """Xóa cache — dùng khi cần reload prompt mà không restart server."""
    load_prompt.cache_clear()
    load_tool_description.cache_clear()
