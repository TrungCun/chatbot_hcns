import gradio as gr

def start_chat_flow(name, phone, email, terms):
    if not name.strip() or not phone.strip() or not email.strip():
        raise gr.Error("Vui lòng điền đầy đủ tên, số điện thoại và email.")
    if not terms:
        raise gr.Error("Bạn cần đồng ý với các điều khoản để tiếp tục.")

    # Định dạng tên_sdt_gmail, thay khoảng trắng trong tên bằng gạch dưới
    user_info = f"{name.strip()}_{phone.strip()}_{email.strip()}".replace(" ", "_")
    user_id = phone.strip()
    session_id = f"{user_id}_000000"

    welcome_message = [{"role": "assistant", "content": "👋 Chào mừng bạn đến với hệ thống tuyển dụng của AIPT! Bạn có thể chọn một vị trí đang tuyển ở danh sách bên trái để xem chi tiết, hoặc có thể gửi file CV/trực tiếp trò chuyện với tôi về vị trí bạn đang quan tâm nhé."}]

    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(value=user_id),
        gr.update(value=session_id),
        gr.update(value=user_info),
        welcome_message
    )
