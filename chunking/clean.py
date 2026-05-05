import re
import os
from pathlib import Path
import re

def clean_ocr_markdown(text: str) -> str:
    # 1. Xóa các thẻ Page sinh ra do scan (VD: ## Page 5)
    text = re.sub(r'(?i)^#*\s*Page\s+\d+\s*$', '', text, flags=re.MULTILINE)
    
    # 2. Xóa các link hình ảnh rác 
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # 3. Phục hồi thẻ Markdown cấp 1 (#) cho CHƯƠNG
    text = re.sub(r'^(CHƯƠNG\s+[IVXLCDM]+\b.*)$', r'# \1', text, flags=re.MULTILINE)
    
    # 4. Phục hồi thẻ Markdown cấp 2 (##) cho ĐIỀU
    text = re.sub(r'^(Điều\s+\d+\..*)$', r'## \1', text, flags=re.MULTILINE)
    
    # --- MỚI THÊM: DỌN DẸP BẢNG HTML RÁC ---
    # Xóa toàn bộ khối <table>...</table> sinh ra do OCR bị lỗi bảng trống
    text = re.sub(r'<table.*?>.*?</table>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # ---------------------------------------
    
    # 5. Dọn dẹp khoảng trắng thừa
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def main():
    # Đường dẫn file đầu vào do bạn cung cấp
    input_file_path = "/home/trung-ai/chatbot_hcns/124ebf20b3df468995e5dd4829d1b357 (1).md"
    
    # Kiểm tra file có tồn tại không
    if not os.path.exists(input_file_path):
        print(f"❌ Lỗi: Không tìm thấy file gốc tại {input_file_path}")
        return

    # Khởi tạo đường dẫn file đầu ra an toàn
    input_path_obj = Path(input_file_path)
    output_file_path = input_path_obj.with_name(f"{input_path_obj.stem}_cleaned{input_path_obj.suffix}")

    print(f"⏳ Đang đọc file: {input_path_obj.name}...")
    
    try:
        # Đọc dữ liệu gốc
        with open(input_file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        print("🧹 Đang tiến hành làm sạch và chuẩn hóa thẻ Markdown...")
        # Tiến hành làm sạch
        cleaned_text = clean_ocr_markdown(raw_text)

        # Lưu dữ liệu đã làm sạch
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        print("-" * 50)
        print(f"✅ Đã làm sạch thành công!")
        print(f"📁 Dữ liệu mới được lưu tại: {output_file_path}")
        
    except Exception as e:
        print(f"❌ Đã xảy ra lỗi trong quá trình xử lý: {e}")

if __name__ == "__main__":
    main()