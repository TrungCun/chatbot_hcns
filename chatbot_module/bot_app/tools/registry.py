from typing import Any, Dict, List
from langchain_core.tools import BaseTool

from bot_app.tools.list_all_jobs import list_all_jobs
from bot_app.tools.retrieve_from_vector_database import retrieve_from_vector_database
from bot_app.tools.check_jobs import check_jobs

from bot_app.log import get_logger
logger = get_logger(__name__)

TOOLS_REGISTRY: Dict[str, BaseTool] = {
    "list_all_jobs": list_all_jobs,
    "retrieve_from_vector_database": retrieve_from_vector_database,
    "check_jobs": check_jobs,
}

def get_tools() -> List[BaseTool]:
    return list(TOOLS_REGISTRY.values())

async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    if tool_name not in TOOLS_REGISTRY:
        logger.warning(f"[REGISTRY] LLM hallucinated unknown tool: {tool_name}")
        return f"Error: Tool '{tool_name}' is not registered in TOOLS_REGISTRY. Available tools are: {list(TOOLS_REGISTRY.keys())}"

    try:
        tool = TOOLS_REGISTRY[tool_name]
        return await tool.ainvoke(tool_input)
    except Exception as e:
        logger.error(f"[REGISTRY] Tool {tool_name} failed: {str(e)}", exc_info=True)
        return f"Error executing {tool_name}: {str(e)}. Please check your input parameters and try again."