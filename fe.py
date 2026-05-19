import gradio as gr
import uuid
import json
import time
import os
import requests

STREAM_URL = "http://localhost:9060/api/chat/stream"

def generate_uuid():
    return str(uuid.uuid4())

def respond(message, chat_history, session_id, user_id):
    start_time = time.time()

    text_input = message.get("text", "")
    uploaded_files = message.get("files", [])

    # Đảm bảo chat_history luôn khởi tạo
    if chat_history is None:
        chat_history = []

    # ==========================================
    # 1. XỬ LÝ FILE: BẮT BUỘC DÙNG gr.FileData
    # ==========================================
    if uploaded_files:
        for file_obj in uploaded_files:
            file_path = None

            if isinstance(file_obj, dict):
                file_path = file_obj.get("path")
            elif hasattr(file_obj, "path"):
                file_path = file_obj.path
            else:
                file_path = str(file_obj)

            if file_path and os.path.exists(file_path):
                chat_history.append({
                    "role": "user",
                    "content": gr.FileData(path=file_path)
                })

    # ==========================================
    # 2. XỬ LÝ TEXT: ĐỊNH DẠNG DICTIONARY
    # ==========================================
    if text_input:
        chat_history.append({
            "role": "user",
            "content": text_input
        })

    # Thêm tin nhắn chờ của Bot
    chat_history.append({
        "role": "assistant",
        "content": "Chờ xíu bé ơi"
    })

    # yield lần 1: Dọn dẹp ô nhập liệu
    yield {"text": "", "files": []}, chat_history, session_id, user_id, "Chờ xíu bé ơi"

    # ==========================================
    # 3. CHUẨN BỊ REQUEST
    # ==========================================
    form_data = {"session_id": session_id, "user_id": user_id}
    if text_input:
        form_data["message"] = text_input

    files_multipart = []
    for file_obj in uploaded_files:
        file_path = None
        if isinstance(file_obj, dict):
            file_path = file_obj.get("path")
        elif hasattr(file_obj, "path"):
            file_path = file_obj.path
        else:
            file_path = str(file_obj)

        if file_path and os.path.exists(file_path):
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            files_multipart.append(
                ("files", (filename, content, "application/octet-stream"))
            )

    # ==========================================
    # 4. NHẬN STREAM & CẬP NHẬT UI THEO TỪNG TOKEN
    # ==========================================
    new_session_id = session_id
    bot_response = ""
    first_token_time = None

    try:
        with requests.post(
            STREAM_URL,
            data=form_data,
            files=files_multipart if files_multipart else None,
            stream=True,
            timeout=180,
        ) as resp:
            resp.raise_for_status()

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if not line.startswith("data: "):
                    continue

                try:
                    event = json.loads(line[len("data: "):])
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                if event_type == "token":
                    if first_token_time is None:
                        first_token_time = time.time()
                    bot_response += event.get("content", "")
                    chat_history[-1]["content"] = bot_response
                    ttft = f"{first_token_time - start_time:.2f}s"
                    yield {"text": "", "files": []}, chat_history, session_id, user_id, ttft

                elif event_type == "done":
                    new_session_id = event.get("session_id", session_id)
                    break

                elif event_type == "error":
                    bot_response = f"❌ Lỗi: {event.get('detail', 'Không rõ')}"
                    chat_history[-1]["content"] = bot_response
                    break

    except requests.HTTPError as e:
        bot_response = f"❌ Lỗi từ server: {e.response.status_code} - {e.response.text[:200]}"
        chat_history[-1]["content"] = bot_response
    except Exception as e:
        bot_response = f"❌ Không thể kết nối đến server: {str(e)[:200]}"
        chat_history[-1]["content"] = bot_response

    if not bot_response:
        chat_history[-1]["content"] = "❌ Không nhận được phản hồi từ server."

    ttft_display = f"{first_token_time - start_time:.2f}s" if first_token_time else "N/A"
    yield {"text": "", "files": []}, chat_history, new_session_id, user_id, ttft_display


# ==========================================
# GIAO DIỆN
# ==========================================
with gr.Blocks(title="Chatbot Hệ Thống Tuyển Dụng") as demo:
    with gr.Row():

        # CỘT TRÁI (Bảng thông số)
        with gr.Column(scale=1):
            gr.Markdown("### Vài thứ linh tinh")
            user_display = gr.Textbox(value="user_01", label="User ID", interactive=True)
            session_display = gr.Textbox(value=generate_uuid, label="Session ID", interactive=False)
            time_display = gr.Textbox(value="0.00 giây", label="Thời gian phản hồi", interactive=False)
            new_session_btn = gr.Button("Một câu chuyện mới", variant="primary")

        # CỘT PHẢI (Khung Chatbot)
        with gr.Column(scale=3):
            gr.Markdown("### Đôi lời tâm sự")
            
            # KHÔNG CÓ type="messages", Gradio 5 tự động áp dụng chuẩn mới nhất
            chatbot = gr.Chatbot(height=550)

            chat_input = gr.MultimodalTextbox(
                file_types=["image", ".pdf", ".docx", ".doc", ".txt"],
                file_count="multiple",
                placeholder="Nói gì đi cậu",
                container=False
            )

    # Khai báo sự kiện
    chat_input.submit(
        fn=respond,
        inputs=[chat_input, chatbot, session_display, user_display],
        outputs=[chat_input, chatbot, session_display, user_display, time_display]
    )

    def reset_session(user_id):
        return user_id, generate_uuid(), [], "0.00 giây"

    new_session_btn.click(
        fn=reset_session,
        inputs=[user_display],
        outputs=[user_display, session_display, chatbot, time_display]
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())