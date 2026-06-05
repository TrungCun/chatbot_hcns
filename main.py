from flask import Flask
from flask_socketio import SocketIO
from src import create_app
from src.extensions import socketIO


#  start chatbot
from chatbot_module.chatbot_interface import init_chatbot

app = create_app()

if __name__ == "__main__":

    init_chatbot()

    socketIO.run(
        app=app,
        debug=False,
        use_reloader=False,
        # ssl_context=("ssl//cert.pem", "ssl//key.pem"),
        allow_unsafe_werkzeug=True,
        host=app.config["HOST"],
        port=app.config["PORT"],
    )
