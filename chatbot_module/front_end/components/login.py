import gradio as gr

def render_login_form():
    with gr.Column(visible=True, elem_classes=["login-container"]) as login_interface:
        gr.Markdown("### Nhập thông tin để bắt đầu", elem_classes=["login-title"])
        name_input = gr.Textbox(label="Tên", placeholder="Nhập tên của bạn", elem_classes=["custom-textbox"])
        phone_input = gr.Textbox(label="Số điện thoại", placeholder="Nhập số điện thoại", elem_classes=["custom-textbox"])
        email_input = gr.Textbox(label="Email", placeholder="Nhập email", elem_classes=["custom-textbox"])
        terms_checkbox = gr.Checkbox(label="Tôi đồng ý với các điều khoản sử dụng", elem_classes=["custom-checkbox"])
        start_btn = gr.Button("Bắt đầu chat", variant="primary", elem_classes=["custom-btn", "login-btn"])
        
    return login_interface, name_input, phone_input, email_input, terms_checkbox, start_btn
