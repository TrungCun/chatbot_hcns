from typing import List

from langchain_core import messages
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser

from app.graph.conversation.state import ConversationState
from app.prompt.loader import load_prompt
from app.model.llm import llm, llm_stream

from app.application import application
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
        domain = "chitchat"  # Fallback domain

    # Fallback
    if domain not in ("job", "company", "chitchat"):
        domain = "chitchat"  # Default to chitchat (safe choice)

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

async def handle_chitchat(state: ConversationState) -> dict:
    message = state["message"]
    context = state.get("context")
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:
        prompt = load_prompt("conversation/handle_chitchat")
        chain = prompt | llm_stream | StrOutputParser()

        response = ""
        async for chunk in chain.astream({
            "message": message,
            "context": context,
            "history": filtered_history
        }):
            response += chunk
        
        response = response.strip()
    except Exception as e:
        logger.error(f"[handle_chitchat] LLM Error: {e}")
        response = "Xin lỗi, tôi không hiểu."  

    logger.info(f"[handle_chitchat] response='{response}'")
    return {
                "response": response,
                "history": [AIMessage(content=response)]
                }

async def rewrite_query(state: ConversationState) -> dict:
    message = state["message"]
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
        results = await retrieve_from_vector_database.ainvoke({"prompt": q, "limit": 20})
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


def get_contextualized_query_for_rerank(state: dict) -> str:
    # """
    # Hàm xác định query tốt nhất cho Reranker, tương thích với LangChain messages.
    # """
    # # 1. Ưu tiên số 1: Dùng rewritten_query nếu nhánh trước đó đã xử lý
    # if state.get("rewritten_query"):
    #     return state["rewritten_query"]
        
    # original_msg = state["message"]
    # history = state.get("history", []) 
    
    # # Lọc lấy các message Human và AI (bỏ qua System hay Tool message ban đầu nếu có)
    # filtered_history = [m for m in history if m.type in ["human", "ai"]]
    
    # # 2. Nếu không có lịch sử (câu hỏi đầu tiên), dùng ngay message gốc
    # if not filtered_history:
    #     return original_msg
        
    # # 3. PHƯƠNG ÁN BACKUP: Nhồi trực tiếp history vào message
    # # Chỉ lấy 3 tin nhắn gần nhất để tránh loãng ngữ cảnh
    # recent_history = filtered_history[-3:] 
    
    # context_parts = []
    # for msg in recent_history:
    #     role = "Người dùng" if msg.type == "human" else "Trợ lý"
    #     context_parts.append(f"{role}: {msg.content}")
        
    # context_str = " | ".join(context_parts)
        
    # # Tạo chuỗi truy vấn kết hợp tối ưu cho Cross-Encoder
    # fallback_query = f"Ngữ cảnh: {context_str} . Câu hỏi: {original_msg}"
    
    # return fallback_query
    # 1. Dùng rewritten_query nếu nhánh trước đó đã xử lý
    if state.get("rewritten_query"):
        return state["rewritten_query"]
        
    # 2. Dùng context đã được LLM đúc kết (sạch và chuẩn hơn nối chuỗi)
    if state.get("context") and state["context"] != "Chưa có bối cảnh.":
        return f"{state['context']}. Câu hỏi: {state['message']}"
        
    # 3. Phương án chót: Chỉ dùng message gốc, KHÔNG nối đống history vào
    return state["message"]

async def rerank_documents(state: ConversationState) -> dict:
    # SỬ DỤNG HÀM VỪA TẠO Ở ĐÂY
    query = get_contextualized_query_for_rerank(state)
    documents = state.get("retrieved_documents", [])
    
    if not documents:
        return {"retrieved_documents": []}
        
    
    rerank_model = application.get_model("reranker")
    if not rerank_model:
        logger.warning("[rerank_documents] Reranker model not found, skipping rerank")
        return {"retrieved_documents": documents[:5]}
    
    try:
        # Tạo cặp (query, doc) để rank
        pairs = [[query, doc] for doc in documents]
        
        # Tính toán điểm số
        scores = rerank_model.predict(pairs)
        
        # Sắp xếp và lấy top K 
        # Nếu là câu hỏi phức tạp (complex), lấy nhiều tài liệu hơn để đảm bảo đủ thông tin tổng hợp
        complexity = state.get("classify_query_complexity", "simple")
        top_k = 20 if complexity == "complex" else 15
        
        results = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        
        # 1. Đặt ngưỡng tối thiểu (Score Threshold)
        # Bất kỳ tài liệu nào có điểm < 0.05 sẽ bị loại bỏ để tránh nhiễu
        score_threshold = 0.2
        filtered_results = [(doc, score) for doc, score in results if score >= score_threshold]
        
        # 2. Giới hạn trên (Cap)
        # Nếu là câu hỏi phức tạp lấy tối đa 20, đơn giản lấy tối đa 15
        complexity = state.get("classify_query_complexity", "simple")
        limit_k = 20 if complexity == "complex" else 15
        
        top_results = filtered_results[:limit_k]
        reranked_docs = [doc for doc, score in top_results]
        
        logger.info(f"[rerank_documents] complexity={complexity}, threshold={score_threshold}, filtered {len(documents)} -> {len(reranked_docs)} docs")
        
        # Log chi tiết các tài liệu đã chọn để debug
        for i, (doc, score) in enumerate(top_results):
            # Lấy 200 ký tự đầu để xem nội dung
            preview = doc.replace("\n", " ")
            logger.info(f"  [Top {i+1}] [Score: {score:.4f}] {preview}...")
            
        return {"retrieved_documents": reranked_docs}
        
    except Exception as e:
        logger.error(f"[rerank_documents] Error: {e}")
        return {"retrieved_documents": documents[:5]}

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
    if not retrieved_docs:
        # Nếu không có tài liệu nào vượt qua được Reranker (đặc biệt cho domain 'company')
        # Chúng ta trả về câu trả lời an toàn thay vì để LLM tự suy diễn
        fallback_msg = "Xin lỗi, hiện tại tôi chưa có thông tin chính thức về vấn đề này trong bộ quy định của công ty. Bạn vui lòng liên hệ trực tiếp với phòng Hành chính - Nhân sự để được giải đáp chính xác nhất nhé!"
        
        logger.info("[generate_response] No documents found after rerank. Using fallback response.")
        return {
            "response": fallback_msg,
            "history": [AIMessage(content=fallback_msg)]
        }
    
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

        # Call LLM với hỗ trợ streaming
        response = None
        async for chunk in llm_with_tools.astream(messages):
            if response is None:
                response = chunk
            else:
                response += chunk
        
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