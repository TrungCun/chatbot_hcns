import gradio as gr
from front_end.utils.helpers import generate_uuid

def render_chat_interface(initial_choices=None, initial_jobs=None):
    if initial_choices is None:
        initial_choices = []
    if initial_jobs is None:
        initial_jobs = []
        
    with gr.Row(visible=False) as chat_interface:
        # CỘT TRÁI (Bảng thông số)
        with gr.Column(scale=1, elem_classes=["sidebar-panel"]):
            gr.Markdown("### Thông tin phiên", elem_classes=["sidebar-title"])
            user_display = gr.Textbox(value="", label="User ID", interactive=False, elem_classes=["custom-textbox"])
            session_display = gr.Textbox(value="", label="Session ID", interactive=False, elem_classes=["custom-textbox"])
            time_display = gr.Textbox(value="0.00s", label="Thời gian phản hồi", interactive=False, elem_classes=["custom-textbox"])
            total_time_display = gr.Textbox(value="0.00s", label="Thời gian hoàn thành (Streaming xong)", interactive=False, elem_classes=["custom-textbox"])
            reset_btn = gr.Button("🔙 Trở lại Chat Chung", variant="secondary")
            
            gr.Markdown("### Vị trí đang tuyển", elem_classes=["sidebar-title"])
            jobs_radio = gr.Radio(choices=initial_choices, label="", elem_classes=["jobs-radio"])
            jobs_state = gr.State(initial_jobs)

        # CỘT PHẢI (Khung Chatbot)
        with gr.Column(scale=3):
            gr.Markdown("### Đôi lời tâm sự")
            
            with gr.Column(elem_classes=["chat-wrapper-box"]):
                # KHÔNG CÓ type="messages", Gradio 5 tự động áp dụng chuẩn mới nhất
                chatbot = gr.Chatbot(height=550, elem_classes=["custom-chatbot"])

                chat_input = gr.MultimodalTextbox(
                    file_types=["image", ".pdf", ".docx", ".doc", ".txt"],
                    file_count="multiple",
                    placeholder="Nói gì đi cậu",
                    container=False,
                    elem_classes=["custom-chatinput"]
                )
            
    return chat_interface, user_display, session_display, time_display, total_time_display, chatbot, chat_input, jobs_radio, jobs_state, reset_btn
