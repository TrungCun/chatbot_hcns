import json
import os
import argparse
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_core.documents import Document

def upload_to_qdrant(json_file_path, collection_name="hcns_knowledge_base"):
    # --- Cấu hình thông số ---
    model_name = "/home/trung-ai/chatbot_hcns/weights/embeddinggemma-300m"
    
    if not os.path.exists(json_file_path):
        print(f"❌ Không tìm thấy file JSON: {json_file_path}")
        return

    # 1. Khởi tạo mô hình Embedding
    print(f"⏳ Đang tải mô hình Dense (Gemma-300m)...")
    dense_embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': 'cuda', 'trust_remote_code': True}, 
        encode_kwargs={'normalize_embeddings': True} 
    )

    # Khởi tạo mô hình Sparse (BM25)
    print("⏳ Đang tải mô hình Sparse (BM25)...")
    sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

    print("🔌 Đang kết nối tới Qdrant (localhost:6333)...")
    client = QdrantClient(url="http://localhost:6333")

    # 2. Kiểm tra/Tạo Collection
    if not client.collection_exists(collection_name=collection_name):
        print(f"🔨 Collection chưa tồn tại. Đang tạo mới Collection Hybrid: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense-embedding": models.VectorParams(
                    size=768, 
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse-embedding": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            }
        )
    else:
        print(f"✅ Collection '{collection_name}' đã tồn tại. Tiến hành nạp thêm dữ liệu...")

    # 3. Đọc dữ liệu từ file Staging JSON
    print(f"📂 Đang đọc chunks từ: {json_file_path}")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)

    # Chuyển đổi dữ liệu thô thành danh sách Document của LangChain
    docs = [
        Document(page_content=item["page_content"], metadata=item["metadata"])
        for item in chunks_data
    ]

    # 4. Thực thi Nhúng Hybrid và đẩy dữ liệu (Ingestion)
    print(f"📥 Đang nhúng và nạp thêm {len(docs)} chunks vào Qdrant...")
    qdrant = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=dense_embeddings,
        sparse_embedding=sparse_embeddings,
        retrieval_mode=RetrievalMode.HYBRID,
        vector_name="dense-embedding",
        sparse_vector_name="sparse-embedding"
    )

    # Hàm add_documents sẽ tự động nạp thêm (upsert) chứ không xóa dữ liệu cũ
    doc_ids = qdrant.add_documents(documents=docs)

    print("=" * 60)
    print(f"🚀 Đã nạp thành công {len(doc_ids)} vectors vào Collection hiện tại.")
    print("=" * 60)

if __name__ == "__main__":
    import glob
    
    # Thư mục chứa các file JSON chunks đã tạo từ bước chunking
    staging_dir = "/home/trung-ai/chatbot_hcns/create_documents/json_chunking"
    
    # Tìm tất cả các file .json trong thư mục
    json_files = glob.glob(os.path.join(staging_dir, "*.json"))
    
    if not json_files:
        print(f"❌ Không tìm thấy file JSON nào trong thư mục: {staging_dir}")
    else:
        print(f"🚀 Tìm thấy {len(json_files)} file JSON. Bắt đầu quá trình upload lên Qdrant...")
        
        for json_file in json_files:
            file_name = os.path.basename(json_file)
            print(f"\n>>>> ⏳ Đang xử lý upload file: {file_name} <<<<")
            try:
                upload_to_qdrant(json_file)
            except Exception as e:
                print(f"❌ Lỗi khi upload file {file_name}: {e}")
                
        print("\n" + "=" * 60)
        print(f"✅ HOÀN TẤT TẤT CẢ QUÁ TRÌNH UPLOAD!")
        print(f"📊 Tổng số file đã xử lý: {len(json_files)}")
        print("=" * 60)
