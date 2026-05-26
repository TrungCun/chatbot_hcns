import json
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

async def validate_retrieval(state: ConversationState) -> dict:
    message = state.get("message", "")
    context = state.get("context") or ""
    domain = state.get("domain")
    loop_count = state.get("loop_count", 0)
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    # 1. Thu thập dữ liệu cần validate tùy theo domain
    retrieved_data = ""
    if domain == "job":
        # fetch lại dữ liệu jobs đã lấy để validate chất lượng
        from app.tools.registry import execute_tool
        jobs_result = await execute_tool("list_all_jobs", {})
        retrieved_data = json.dumps(jobs_result, ensure_ascii=False)
    else:
        # Nhánh company: dùng kết quả từ Rerank
        docs = state.get("retrieved_documents", [])
        retrieved_data = "\n\n".join(docs)

    # Nếu đây là lần loop thứ 2, hoặc là chitchat, cho qua luôn
    if loop_count >= 1 or domain == "chitchat" or not message:
        return {"validation_result": "pass"}

    if not retrieved_data:
        logger.warning("[validate_retrieval] No data retrieved. Failing to trigger retry.")
        return {"validation_result": "fail", "loop_count": loop_count + 1}

    try:
        prompt_template = load_prompt("conversation/validate_retrieval")
        chain = prompt_template | llm | StrOutputParser()

        result = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history,
            "retrieved_data": retrieved_data[:8000]
        })

        validation = "pass" if "pass" in result.strip().lower() else "fail"
        logger.info(f"[validate_retrieval] domain={domain}, result={validation}, attempt={loop_count + 1}")

        return {
            "validation_result": validation,
            "loop_count": loop_count + 1 if validation == "fail" else loop_count
        }
    except Exception as e:
        logger.error(f"[validate_retrieval] Error: {e}")
        return {"validation_result": "pass"}

async def handle_job_query(state: ConversationState) -> dict:
    from app.tools.registry import execute_tool

    message = state.get("message", "")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    logger.info(f"[handle_job_query] processing job query: '{message}'")

    try:
        # 1. LLM sinh câu SQL từ câu hỏi người dùng
        sql_prompt = load_prompt("conversation/generate_sql_job")
        sql_chain = sql_prompt | llm | StrOutputParser()
        sql_query = await sql_chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history,
        })
        sql_query = sql_query.strip()
        logger.info(f"[handle_job_query] generated SQL: {sql_query}")

        # 2. Validate chỉ cho phép SELECT
        if not sql_query.upper().lstrip().startswith("SELECT"):
            logger.warning("[handle_job_query] Invalid SQL generated, using fallback")
            sql_query = "SELECT rc.id, rc.name, rc.jd_job_description, rc.jd_salary_range, rr.quantity FROM recruitment_campaigns rc JOIN recruitment_requests rr ON rc.request_id = rr.id WHERE rc.status = 1 LIMIT 10"

        # 3. Gọi tool check_jobs với SQL đã sinh
        jobs_result = await execute_tool("check_jobs", {"query": sql_query})
        jobs_data = json.dumps(jobs_result, ensure_ascii=False, indent=2) if isinstance(jobs_result, (dict, list)) else str(jobs_result)

        # 4. LLM sinh phản hồi dựa trên kết quả trả về
        response_prompt = load_prompt("conversation/handle_job")
        chain = response_prompt | llm_stream | StrOutputParser()

        response = ""
        async for chunk in chain.astream({
            "message": message,
            "context": context,
            "history": filtered_history,
            "jobs_data": jobs_data
        }):
            response += chunk

        response = response.strip()
    except Exception as e:
        logger.error(f"[handle_job_query] Error: {e}")
        response = "Xin lỗi, hiện tại tôi gặp khó khăn khi tra cứu danh sách công việc. Bạn vui lòng thử lại sau hoặc tham khảo website tuyển dụng của công ty nhé!"

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
        # Mặc định lấy top 20 tài liệu chất lượng nhất sau khi rerank
        top_k = 20

        results = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

        # 1. Đặt ngưỡng tối thiểu (Score Threshold)
        # Bất kỳ tài liệu nào có điểm < 0.2 sẽ bị loại bỏ để tránh nhiễu
        score_threshold = 0.2
        filtered_results = [(doc, score) for doc, score in results if score >= score_threshold]

        # 2. Giới hạn trên (Cap)
        limit_k = 20

        top_results = filtered_results[:limit_k]
        reranked_docs = [doc for doc, score in top_results]

        logger.info(f"[rerank_documents] threshold={score_threshold}, filtered {len(documents)} -> {len(reranked_docs)} docs")
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
    from app.prompt.loader import load_prompt

    logger.info(f"[generate_response] message='{state['message']}', documents={len(state.get('retrieved_documents', []))}")

    message = state.get("message", "")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    retrieved_docs = state.get("retrieved_documents", [])
    if not retrieved_docs:
        # Nếu không có tài liệu nào vượt qua được Reranker (đặc biệt cho domain 'company')
        fallback_msg = "Xin lỗi, hiện tại tôi chưa tìm thấy thông tin chính thức về vấn đề này trong bộ quy định của công ty. Bạn vui lòng liên hệ trực tiếp với phòng Hành chính - Nhân sự để được giải đáp chính xác nhất nhé!"

        logger.info("[generate_response] No documents found after rerank. Using fallback response.")
        return {
            "response": fallback_msg,
            "history": [AIMessage(content=fallback_msg)]
        }

    knowledge_context = "\n\n".join([f"--- Tài liệu {i+1} ---\n{doc}" for i, doc in enumerate(retrieved_docs)])

    # 1. Load RAG prompt
    agent_prompt = load_prompt("conversation/generate_response_02")

    try:
        # 2. Sử dụng llm_stream để sinh phản hồi dựa trên context trích xuất
        chain = agent_prompt | llm_stream | StrOutputParser()

        response = ""
        async for chunk in chain.astream({
            "context": context,
            "history": filtered_history,
            "message": message,
            "knowledge_context": knowledge_context
        }):
            response += chunk

        response = response.strip()

        logger.info("[generate_response] Successfully generated RAG response")
        return {
            "response": response,
            "history": [AIMessage(content=response)]
        }

    except Exception as e:
        logger.error(f"[generate_response] LLM Error: {e}")
        return {
            "response": "Xin lỗi, hệ thống đang gặp lỗi khi tổng hợp câu trả lời. Bạn vui lòng thử lại sau.",
            "history": [AIMessage(content="Lỗi hệ thống khi generate response")]
        }

async def evaluate_response(state: ConversationState) -> dict:
    # Gỡ bỏ logic evaluate cũ để chuyển sang tiền kiểm (validate_retrieval)
    return {"evaluation_result": "pass"}
