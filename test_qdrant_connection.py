"""
Test kết nối tới Qdrant.
Chạy: conda run -n chatbothcns python test_qdrant_connection.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")


def test_connection():
    from qdrant_client import QdrantClient

    print(f"Connecting to: {QDRANT_URL}")

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY or None,
        timeout=10,
    )

    # 1. Liệt kê collections (đủ để xác nhận kết nối + auth OK)
    collections = client.get_collections().collections
    names = [c.name for c in collections]
    print(f"[OK] Collections ({len(names)}): {names}")

    # 2. Thông tin version
    try:
        info = client.info()
        print(f"[OK] Qdrant version: {info.version}")
    except Exception as e:
        print(f"[WARN] Không lấy được version: {e}")

    print("\nKết nối Qdrant thành công!")


if __name__ == "__main__":
    try:
        test_connection()
    except Exception as e:
        print(f"\n[FAIL] Kết nối thất bại: {e}")
        raise SystemExit(1)
