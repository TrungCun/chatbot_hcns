from app.tools.list_all_jobs import list_all_jobs

from app.log import get_logger
logger = get_logger(__name__)

TOOLS_REGISTRY = {
    "list_all_jobs": list_all_jobs,
}

def get_tools():
    return list(TOOLS_REGISTRY.values())

async def execute_tool(tool_name: str, tool_input: dict):
    if tool_name not in TOOLS_REGISTRY:
        return f"Error: Tool '{tool_name}' is not registered in TOOLS_REGISTRY. Available tools are: {list(TOOLS_REGISTRY.keys())}"

    try:
        tool = TOOLS_REGISTRY[tool_name]
        return await tool.ainvoke(tool_input)
    except Exception as e:
        logger.error(f"[SYSTEM ERROR] Tool {tool_name} failed: {str(e)}")
        return f"Error executing {tool_name}: {str(e)}. Please check your input parameters and try again."