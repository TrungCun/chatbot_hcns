# Tối ưu hóa Node Extract Info với Structured Output

Hiện tại, node `extract_info` đang sử dụng LLM để sinh ra một chuỗi văn bản (Text) có định dạng JSON, sau đó parse chuỗi này bằng `CVTemplate.model_validate_json(result)`.
Phương pháp này có một số nhược điểm:
- **Tốn token và thời gian**: LLM phải tốn token để sinh ra các ký tự định dạng (như ngoặc nhọn, ngoặc vuông, khoảng trắng, key string).
- **Rủi ro lỗi cú pháp**: LLM có thể sinh ra JSON không hợp lệ (thiếu dấu phẩy, thừa dấu ngoặc).

## Giải pháp: Sử dụng `with_structured_output`

Langchain hỗ trợ hàm `with_structured_output()`, giúp gọi trực tiếp vào API Function Calling hoặc JSON Schema Mode gốc của các LLM (như OpenAI, Gemini). 
Thay vì prompt LLM trả về Text, tính năng này ép LLM trả về đúng Object (Pydantic Model) mà ta mong muốn.

### Lợi ích:
1. **Tốc độ cực nhanh**: Giảm đáng kể lượng token sinh ra, giúp rút ngắn thời gian sinh text từ 7 giây xuống mức thấp hơn rất nhiều.
2. **Độ ổn định 100%**: LLM tự động tuân thủ chặt chẽ Schema của Pydantic, không bao giờ bị lỗi Syntax Error khi parse JSON.

### Code mẫu để thay thế (trong `bot_app/graph/summary/nodes.py`)

**Đoạn code cũ:**
```python
        prompt = load_prompt("summary/extract_info")
        chain = prompt | llm
        response = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history,
            "available_jobs": available_jobs_str
        })

        result = response.content
        result_obj = CVTemplate.model_validate_json(result)
```

**Đoạn code tối ưu (Bạn có thể copy/paste thay thế sau này):**
```python
        prompt = load_prompt("summary/extract_info")
        
        # Bọc LLM với cấu trúc Pydantic mong muốn
        structured_llm = llm.with_structured_output(CVTemplate)
        
        chain = prompt | structured_llm
        
        # Gọi ainvoke sẽ trả về thẳng object CVTemplate, không cần parse json bằng chuỗi text nữa
        result_obj = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history,
            "available_jobs": available_jobs_str
        })
```

> [!NOTE]
> **Lưu ý khi áp dụng**: Tùy thuộc vào model bạn đang dùng (Gemini hay GPT) và phiên bản thư viện `langchain`, đôi khi hàm `with_structured_output` yêu cầu model phải hỗ trợ Native Function Calling. Nếu gặp lỗi trả về Object rỗng hoặc không đúng định dạng, bạn có thể truyền thêm tham số `method="json_mode"` hoặc kiểm tra lại version của `langchain-core`.
