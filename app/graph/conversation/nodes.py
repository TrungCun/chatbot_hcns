from typing import List
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.graph.conversation.state import ConversationState
from app.prompt.loader import load_prompt
from app.model.llm import get_llm

from app.log import get_logger
logger = get_logger(__name__)

def _make_llm() -> ChatOpenAI:
    return get_llm(stream=False)


def _parse_lines(text: str) -> List[str]:
    return [line.strip() for line in text.strip().splitlines() if line.strip()]

async def classify_conversation_domain(state: ConversationState) -> dict:
    """Level 2 Classification: Determine conversation domain for 'ask' intent.
    Returns: domain = 'job' | 'company'

    Only called if intent = 'ask'. Routes questions to appropriate handler:
    - 'job': Use list_all_jobs tool (direct lookup, no RAG)
    - 'company': Use RAG pipeline (full context retrieval)
    """
    message = state["message"]
    logger.info(f"[classify_conversation_domain] message='{message}'")

    llm = get_llm(stream=False)
    chain = load_prompt("conversation/classify_domain") | llm | StrOutputParser()

    result = await chain.ainvoke({"message": message})
    domain = result.strip().lower()

    # Fallback
    if domain not in ("job", "company"):
        domain = "company"  # Default to company (safe choice)

    logger.info(f"[classify_conversation_domain] domain='{domain}'")
    return {"domain": domain}

async def classify_query_complexity(state: ConversationState) -> dict:
    """Level 3 Classification: Determine RAG query complexity.
    Returns: classify_query_complexity = 'simple' | 'complex' | 'factual'

    - 'simple': Single-step retrieval needed
    - 'complex': Multi-step decomposition needed
    - 'factual': Hypothetical document generation helpful
    """
    logger.info(f"[classify_query_complexity] question='{state['message']}'")
    llm = _make_llm()
    chain = load_prompt("conversation/analyze_query") | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["message"]})
    classify_query_complexity = result.strip().lower()

    # Fallback
    if classify_query_complexity not in ("simple", "complex", "factual"):
        classify_query_complexity = "simple"

    logger.info(f"[classify_query_complexity] classify_query_complexity='{classify_query_complexity}'")
    return {"classify_query_complexity": classify_query_complexity}


async def rewrite_query(state: ConversationState) -> dict:
    logger.info("[rewrite_query] rewriting simple query")
    llm = _make_llm()
    chain = load_prompt("conversation/rewrite_query") | llm | StrOutputParser()
    rewritten = await chain.ainvoke({"question": state["message"]})
    rewritten = rewritten.strip()
    logger.info(f"[rewrite_query] result='{rewritten}'")
    return {"rewritten_query": rewritten, "final_queries": [rewritten]}


async def decompose_query(state: ConversationState) -> dict:
    logger.info("[decompose_query] decomposing complex query")
    llm = _make_llm()
    chain = load_prompt("conversation/decompose_query") | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["message"]})
    sub_questions = _parse_lines(result)

    if not sub_questions:
        sub_questions = [state["message"]]

    logger.info(f"[decompose_query] sub_questions={sub_questions}")
    return {"sub_questions": sub_questions, "final_queries": sub_questions}


async def hyde_query(state: ConversationState) -> dict:
    logger.info("[hyde_query] generating hypothetical document")
    llm = _make_llm()
    chain = load_prompt("conversation/hyde_query") | llm | StrOutputParser()
    hyde_doc = await chain.ainvoke({"question": state["message"]})
    hyde_doc = hyde_doc.strip()
    logger.info(f"[hyde_query] hyde_document length={len(hyde_doc)}")
    return {"hyde_document": hyde_doc, "final_queries": [state["message"], hyde_doc]}



async def expand_queries(state: ConversationState) -> dict:
    logger.info(f"[expand_queries] expanding {len(state['final_queries'])} queries")
    llm = _make_llm()
    chain = load_prompt("conversation/expand_queries") | llm | StrOutputParser()

    all_queries: List[str] = []
    seen: set = set()

    for query in state["final_queries"]:
        if query not in seen:
            all_queries.append(query)
            seen.add(query)

        result = await chain.ainvoke({"question": query, "n": 2})
        for variant in _parse_lines(result):
            if variant not in seen:
                all_queries.append(variant)
                seen.add(variant)

    logger.info(f"[expand_queries] total final_queries={len(all_queries)}")
    response_data = {"final_queries": all_queries}
    import json
    return {
        "final_queries": all_queries,
        "response": json.dumps(response_data, ensure_ascii=False)
    }

async def generate_response(state: ConversationState) -> dict:
    """Agent node: LLM decides which tools to use based on prompt.

    Tools are injected from registry, not hardcoded.
    Tool usage is determined by prompt, not code.
    """
    import json
    from langchain_core.messages import HumanMessage, ToolMessage
    from app.model.llm import get_llm
    from app.prompt.loader import load_prompt
    from app.tools.registry import get_tools, execute_tool

    logger.info(f"[generate_response] message='{state['message']}'")

    # Load tools and prompt
    tools = get_tools()
    llm = get_llm(stream=False)
    llm_with_tools = llm.bind_tools(tools)

    agent_prompt = load_prompt("conversation/generate_response")

    # Build prompt message
    tools_description = "\n".join([f"- {t.name}: {t.description}" for t in tools])
    prompt_value = agent_prompt.invoke({
        "input": state["message"],
        "tools_description": tools_description
    })

    # Extract message content
    message_content = prompt_value.content if hasattr(prompt_value, 'content') else str(prompt_value)
    messages = [HumanMessage(content=message_content)]

    # Agent loop (max 3 iterations)
    max_iterations = 3
    for iteration in range(max_iterations):
        logger.info(f"[generate_response] iteration {iteration + 1}")

        # Call LLM
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        # Check: có tool calls?
        if not response.tool_calls:
            logger.info("[generate_response] no tools, returning response")
            return {"response": response.content}

        # Execute tools
        logger.info(f"[generate_response] executing {len(response.tool_calls)} tools")

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call.get("args", {})

            logger.info(f"[generate_response] calling {tool_name}")
            result = await execute_tool(tool_name, tool_input)

            messages.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
            ))

    # Fallback
    return {"response": "Không thể xử lý câu hỏi này"}
