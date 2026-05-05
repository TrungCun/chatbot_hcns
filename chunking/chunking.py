import os
import unicodedata
from transformers import AutoTokenizer
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def normalize_vietnamese_text(text: str) -> str:
    """Chuẩn hóa Unicode tiếng Việt về chuẩn dựng sẵn NFC"""
    return unicodedata.normalize("NFC", text)

def process_markdown_for_rag_production(markdown_text: str, model_id_or_path: str):
    # 0. Tiền xử lý văn bản
    clean_text = normalize_vietnamese_text(markdown_text)

    # 1. Tách theo Header cấu trúc (Giữ nguyên như cũ)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    md_header_splits = markdown_splitter.split_text(clean_text)
    
    # 2. Khởi tạo Tokenizer của chính model Gemma bạn đang dùng
    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
    
    # 3. Sử dụng HuggingFace Tokenizer Splitter (Cắt theo Token, KHÔNG cắt theo Ký tự)
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer=tokenizer,
        chunk_size=400,
        chunk_overlap=50,
        # Ưu tiên cắt ở: Đoạn mới -> Điểm số (1.) -> Điểm chữ (a.) -> Dấu câu
        separators=[
            "\n\n", 
            "\n1. ", "\n2. ", "\n3. ", "\n4. ", "\n5. ", 
            "\na. ", "\nb. ", "\nc. ", "\nd. ", 
            "\n", ".", ";", " ", ""
        ]
    )
    
    # 4. Cắt nhỏ các chunk
    final_splits = text_splitter.split_documents(md_header_splits)
    
    # 5. Gắn Metadata / Breadcrumb (Context Enrichment)
    for doc in final_splits:
        metadata = doc.metadata
        path = " > ".join([v for k, v in metadata.items() if k.startswith("Header")])
        if path:
            doc.page_content = f"[{path}]\n{doc.page_content}"
            
    return final_splits

# ─────────────────────────── ENTRY POINT ───────────────────────────

def main():
    print(">>> BẮT ĐẦU TEST CHUNKING <<<")
    
    # Sử dụng file đã qua xử lý clean_text.py
    file_path = "/home/trung-ai/chatbot_hcns/124ebf20b3df468995e5dd4829d1b357 (1)_cleaned.md"
    
    model_id_or_path = "/home/trung-ai/chatbot_hcns/weights/embeddinggemma-300m" 
    
    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file: {file_path}")
        return
        
    print(f"⏳ Đang đọc nội dung file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
        
    print(f"⚙️ Đang tiến hành phân tách với tokenizer của model: {model_id_or_path}...")
    try:
        chunks = process_markdown_for_rag_production(markdown_text, model_id_or_path)
        
        print("=" * 50)
        print(f"✅ Chunking thành công! Tổng số chunks tạo ra: {len(chunks)}")
        print("=" * 50)
        
        # In thử 3 chunk đầu tiên để kiểm tra trực quan
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n--- 📦 Chunk {i + 1} ---")
            print(f"Độ dài (ký tự): {len(chunk.page_content)}")
            print(f"Nội dung:\n{chunk.page_content}")
            print("-" * 40)
            
        print("\n🚀 Sẵn sàng tạo endpoint API CRUD để đưa các chunk này vào Vector DB!")
        
    except Exception as e:
        print(f"❌ Lỗi trong quá trình chunking: {e}")

if __name__ == "__main__":
    main()