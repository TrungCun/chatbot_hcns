from app.tools.list_all_jobs import list_all_jobs
# Sắp tới: from app.tools.search_documents import search_documents
# Sắp tới: from app.tools.extract_info import extract_info

TOOLS_REGISTRY = {
    "list_all_jobs": list_all_jobs,
    # Thêm tool: chỉ add 1 dòng vào đây
}

def get_tools():
    """Return all available tools for LLM."""
    return list(TOOLS_REGISTRY.values())

async def execute_tool(tool_name: str, tool_input: dict):
    """Execute tool by name."""
    if tool_name not in TOOLS_REGISTRY:
        raise ValueError(f"Tool {tool_name} not found")

    tool = TOOLS_REGISTRY[tool_name]
    return await tool.ainvoke(tool_input)