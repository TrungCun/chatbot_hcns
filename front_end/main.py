import gradio as gr
import os
from front_end.components.login import render_login_form
from front_end.components.chat import render_chat_interface
from front_end.handlers.auth import start_chat_flow
from front_end.handlers.chat import respond

# Đọc file CSS
css_path = os.path.join(os.path.dirname(__file__), "styles", "main.css")
css_content = ""
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

# Khởi tạo tạm DB để lấy danh sách jobs cố định cho UI
try:
    from app.tools.mysql import init_mysql, close_mysql
    from front_end.handlers.db import get_active_jobs
    init_mysql()
    initial_jobs = get_active_jobs()
    initial_choices = [job["position_name"] for job in initial_jobs]
    close_mysql()
except Exception as e:
    print(f"Error pre-loading jobs: {e}")
    initial_jobs = []
    initial_choices = []

with gr.Blocks(title="Chatbot Hệ Thống Tuyển Dụng") as demo:
    # 1. Render UI Components
    login_interface, name_input, phone_input, email_input, terms_checkbox, start_btn = render_login_form()
    chat_interface, user_display, session_display, time_display, chatbot, chat_input, jobs_radio, jobs_state, reset_btn = render_chat_interface(initial_choices, initial_jobs)

    # 2. Attach Event Handlers
    # Chuyển trang từ form login sang khung chat và truyền dữ liệu
    start_btn.click(
        fn=start_chat_flow,
        inputs=[name_input, phone_input, email_input, terms_checkbox],
        outputs=[login_interface, chat_interface, user_display, session_display, chatbot]
    )

    # Xử lý chat
    chat_input.submit(
        fn=respond,
        inputs=[chat_input, chatbot, session_display, user_display],
        outputs=[chat_input, chatbot, session_display, user_display, time_display]
    )

    # Xử lý khi chọn job
    def on_job_select(selected_position_name, current_jobs, current_user_id):
        if not selected_position_name or not current_jobs:
            return gr.update(), []
        
        selected_job = next((job for job in current_jobs if job["position_name"] == selected_position_name), None)
        if not selected_job:
            return gr.update(), []
        
        details = []
        details.append(f"**Vị trí:** {selected_job['position_name']}")
        details.append(f"**Số lượng tuyển:** {selected_job['number_of_positions_to_hire']}")
        details.append(f"**Kinh nghiệm tối thiểu:** {selected_job['min_experience_years']}")
        details.append(f"**Yêu cầu học vấn:** {selected_job['education_requirement']}")
        details.append(f"**Mức lương:** {selected_job['salary_range']}")
        details.append(f"**Quyền lợi:** {selected_job['benefits']}")
        details.append(f"**Các vòng phỏng vấn:** {selected_job['interview_rounds']}")
        
        info_text = "\n".join(details)
        
        # Reload (Clear) khung chat, chỉ hiển thị thông tin vị trí mới
        new_chat_history = [{"role": "assistant", "content": f"**Chi tiết vị trí vừa chọn:**\n{info_text}"}]
        
        # Format session_id mới: user_id + campaign_id
        new_session_id = f"{current_user_id}_{selected_job['campaign_id']}"
        
        return gr.update(value=new_session_id), new_chat_history

    jobs_radio.change(
        fn=on_job_select,
        inputs=[jobs_radio, jobs_state, user_display],
        outputs=[session_display, chatbot]
    )

    def on_reset_click(current_user_id):
        new_session_id = f"{current_user_id}_000000"
        welcome_message = [{"role": "assistant", "content": "👋 Chào mừng bạn đến với hệ thống tuyển dụng của AIPT! Bạn có thể chọn một vị trí đang tuyển ở danh sách bên trái để xem chi tiết, hoặc có thể gửi file CV/trực tiếp trò chuyện với tôi về vị trí bạn đang quan tâm nhé."}]
        # Clear jobs_radio by setting value to None
        return gr.update(value=new_session_id), welcome_message, gr.update(value=None)

    reset_btn.click(
        fn=on_reset_click,
        inputs=[user_display],
        outputs=[session_display, chatbot, jobs_radio]
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
