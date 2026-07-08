from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# Chỉ khởi tạo chứ chưa gắn app vào
socketIO = SocketIO(cors_allowed_origins="*")

db = SQLAlchemy()
