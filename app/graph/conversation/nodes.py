from typing import List

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser

from app.graph.conversation.state import ConversationState
from app.prompt.loader import load_prompt
from app.model.llm import llm, llm_stream

from app.log import get_logger
logger = get_logger(__name__)

def _parse_lines(text: str) -> List[str]:
    return [line.strip() for line in text.strip().splitlines() if line.strip()]

async def classify_conversation_domain(state: ConversationState) -> dict:
    message = state["message"]
    attachments = state.get("attachments")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:

        prompt = load_prompt("conversation/classify_domain")
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history
        })
        domain = result.strip().lower()
    except Exception as e:
        logger.error(f"[classify_conversation_domain] LLM Error: {e}")
        domain = "company"  # Fallback domain

    # Fallback
    if domain not in ("job", "company"):
        domain = "company"  # Default to company (safe choice)

    logger.info(f"[classify_conversation_domain] domain='{domain}'")
    return {"domain": domain}

async def classify_query_complexity(state: ConversationState) -> dict:
    message = state["message"]
    attachments = state.get("attachments")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:
        prompt = load_prompt("conversation/analyze_query")
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history
        })
        classify_query_complexity = result.strip().lower()
    except Exception as e:
        logger.error(f"[classify_query_complexity] LLM Error: {e}")
        classify_query_complexity = "simple"  # Fallback complexity

    # Fallback
    if classify_query_complexity not in ("simple", "complex", "factual"):
        classify_query_complexity = "simple"

    logger.info(f"[classify_query_complexity] classify_query_complexity='{classify_query_complexity}'")
    return {"classify_query_complexity": classify_query_complexity}


async def rewrite_query(state: ConversationState) -> dict:
    message = state["message"]
    attachments = state.get("attachments")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:

        prompt = load_prompt("conversation/rewrite_query")
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history
        })
        rewritten = result.strip()
    except Exception as e:
        logger.error(f"[rewrite_query] LLM Error: {e}")
        rewritten = message  # Fallback to original message

    logger.info(f"[rewrite_query] result='{rewritten}'")
    return {"rewritten_query": rewritten, "final_queries": [rewritten]}

async def decompose_query(state: ConversationState) -> dict:
    message = state["message"]
    attachments = state.get("attachments")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:
        prompt = load_prompt("conversation/decompose_query")
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history
        })
        sub_questions = _parse_lines(result)
    except Exception as e:
        logger.error(f"[decompose_query] LLM Error: {e}")
        sub_questions = [state["message"]]  # Fallback to original message

    if not sub_questions:
        sub_questions = [state["message"]]

    logger.info(f"[decompose_query] sub_questions={sub_questions}")
    return {"sub_questions": sub_questions, "final_queries": sub_questions}


async def hyde_query(state: ConversationState) -> dict:
    message = state["message"]
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]
    try:
        prompt = load_prompt("conversation/hyde_query")
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history
        })
        hyde_doc = result.strip()
    except Exception as e:
        logger.error(f"[hyde_query] LLM Error: {e}")
        hyde_doc = message  # Fallback to original message

    logger.info(f"[hyde_query] hyde_document ={hyde_doc}")
    return {"hyde_document": hyde_doc, "final_queries": [state["message"], hyde_doc]}



async def expand_queries(state: ConversationState) -> dict:
    logger.info(f"[expand_queries] expanding {len(state['final_queries'])} queries")
    message = state["message"]
    attachments = state.get("attachments")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:
        prompt = load_prompt("conversation/expand_queries")
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "n": 3,
            "message": message,
            "context": context,
            "history": filtered_history
        })
        formatted_prompt = result.strip()
    except Exception as e:
        logger.error(f"[expand_queries] LLM Error: {e}")
        formatted_prompt = message  # Fallback to original message

    all_queries: List[str] = []
    seen: set = set()

    for query in state["final_queries"]:
        if query not in seen:
            all_queries.append(query)
            seen.add(query)

        result = await llm.ainvoke(formatted_prompt, config={"timeout": 60000})
        for variant in _parse_lines(result.content):
            if variant not in seen:
                all_queries.append(variant)
                seen.add(variant)

    logger.info(f"[expand_queries] total final_queries={len(all_queries)}")
    return {
        "final_queries": all_queries,
    }

async def retrieve_documents(state: ConversationState) -> dict:
    from app.tools.retrieve_from_vector_database import retrieve_from_vector_database
    
    queries = state.get("final_queries") or [state["message"]]
    logger.info(f"[retrieve_documents] retrieving for {len(queries)} queries")
    
    all_docs = []
    seen_contents = set()
    
    for q in queries:
        # Gọi trực tiếp logic của tool
        results = await retrieve_from_vector_database.ainvoke({"prompt": q, "limit": 5})
        for doc in results:
            if isinstance(doc, dict) and "content" in doc:
                content = doc["content"]
                if content not in seen_contents:
                    all_docs.append(content)
                    seen_contents.add(content)
            elif isinstance(doc, str):
                if doc not in seen_contents:
                    all_docs.append(doc)
                    seen_contents.add(doc)
                
    logger.info(f"[retrieve_documents] found {len(all_docs)} unique document chunks")
    return {"retrieved_documents": all_docs}

async def generate_response(state: ConversationState) -> dict:
    import json
    from langchain_core.messages import ToolMessage
    from app.prompt.loader import load_prompt
    from app.tools.registry import get_tools, execute_tool

    logger.info(f"[generate_response] message='{state['message']}', documents={len(state.get('retrieved_documents', []))}")

    message = state.get("message", "")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]
    
    retrieved_docs = state.get("retrieved_documents", [])
    knowledge_context = "\n\n".join([f"--- Tài liệu {i+1} ---\n{doc}" for i, doc in enumerate(retrieved_docs)])

    # Load tools and prompt
    tools = get_tools()
    llm_with_tools = llm_stream.bind_tools(tools)
    
    agent_prompt = load_prompt("conversation/generate_response_02")
    
    messages = agent_prompt.invoke({
        "context": context,
        "history": filtered_history,
        "message": message, 
        "knowledge_context": knowledge_context,
        "tools_description": "\n".join([f"- {t.name}: {t.description}" for t in tools])
    }).to_messages()

    # Re-using tool loop for dynamic tasks like list_all_jobs if needed, 
    # but primarily focusing on retrieved knowledge
    max_iterations = 5
    for iteration in range(max_iterations):
        logger.info(f"[generate_response] iteration {iteration + 1}")

        # Call LLM
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        # Check: có tool calls?
        if not response.tool_calls:
            logger.info("[generate_response] no tools, returning response")
            return {
                "response": response.content,
                "history": [AIMessage(content=response.content)]
                }

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
    return {
        "response": "Bro hỏi khó thế -.-",
        "history": [AIMessage(content="Không thể xử lý câu hỏi này")]
        }
