from datetime import datetime

from sqlalchemy import Column, ForeignKey, Index, Integer, Text, BigInteger

from src.extensions import db


class RecruitmentChatMessage(db.Model):
    __tablename__ = "recruitment_chat_messages"

    __table_args__ = (
        Index(
            "ix_recruitment_chat_messages_session_sequence", "session_id", "sequence_no"
        ),
    )

    id = Column(Integer, primary_key=True)

    session_id = Column(
        Integer,
        ForeignKey("recruitment_chat_sessions.id"),
        nullable=False,
        index=True,
    )

    role = Column(Integer, nullable=False)
    # 1=user, 2=assistant, 3=system

    content = Column(Text, nullable=False)

    message_type = Column(Integer, nullable=False, default=1)
    # 1=text, 2=form, 3=file_upload, 4=action, 5=jd

    payload = Column(Text, nullable=True)

    sequence_no = Column(Integer, nullable=False)

    created_at = Column(BigInteger)

    session = db.relationship(
        "RecruitmentChatSession",
        back_populates="messages",
    )

    def __init__(self, **kwargs):
        super(RecruitmentChatMessage, self).__init__(**kwargs)

        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "payload": self.payload,
            "sequence_no": self.sequence_no,
            "created_at": self.created_at,
        }
