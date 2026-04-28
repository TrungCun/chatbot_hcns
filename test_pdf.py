import fitz  # PyMuPDF
import base64

def process_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    images = []

    print(f"Số trang: {len(doc)}")

    for i in range(len(doc)):
        page = doc[i]
        # 1. Thử trích xuất text (dành cho PDF thuần)
        page_text = page.get_text()
        text += f"--- Page {i+1} ---\n{page_text}\n"

        # 2. Render trang thành ảnh (dành cho Vision LLM hoặc PDF dạng ảnh)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # Tăng độ phân giải một chút
        img_data = pix.tobytes("png")
        base64_img = base64.b64encode(img_data).decode("utf-8")
        images.append(base64_img)

    doc.close()
    return text, images

if __name__ == "__main__":
    pdf_path = "/home/trung-ai/chatbot_hcns/Trần Đức Anh - TTS Presales Phần cứng.pdf"
    try:
        content, imgs = process_pdf(pdf_path)
        print("--- NỘI DUNG TEXT TRÍCH XUẤT ---")
        print(content[:1000]) # In 1000 ký tự đầu
        print(f"\nĐã convert {len(imgs)} trang thành ảnh base64.")
    except Exception as e:
        print(f"Lỗi: {e}")
