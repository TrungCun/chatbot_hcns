from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, Text, BigInteger

from src.extensions import db


class RecruitmentChatSession(db.Model):
    __tablename__ = "recruitment_chat_sessions"

    id = Column(Integer, primary_key=True)

    campaign_id = Column(
        Integer,
        ForeignKey("recruitment_campaigns.id"),
        nullable=True,
        index=True,
    )

    candidate_id = Column(
        Integer,
        ForeignKey("recruitment_candidates.id"),
        nullable=True,
        index=True,
    )

    session_token = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    status = Column(Integer, nullable=False, default=1, index=True)
    # 1=active

    user_agent = Column(String(1000), nullable=True)

    context_data = Column(Text, nullable=True)

    started_at = Column(BigInteger)

    ended_at = Column(BigInteger, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    campaign = db.relationship(
        "RecruitmentCampaign",
        back_populates="chat_sessions",
    )

    candidate = db.relationship(
        "RecruitmentCandidate",
        back_populates="chat_sessions",
    )

    messages = db.relationship(
        "RecruitmentChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="RecruitmentChatMessage.sequence_no",
    )

    def __init__(self, **kwargs):
        super(RecruitmentChatSession, self).__init__(**kwargs)

        now = int(datetime.now().timestamp())

        if not self.created_at:
            self.created_at = now

        if not self.updated_at:
            self.updated_at = self.created_at

        if not self.started_at:
            self.started_at = self.created_at

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "candidate_id": self.candidate_id,
            "session_token": self.session_token,
            "status": self.status,
            "user_agent": self.user_agent,
            "context_data": self.context_data,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
