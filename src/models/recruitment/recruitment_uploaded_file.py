from datetime import datetime

from sqlalchemy import Column, ForeignKey, Index, Integer, String, BigInteger, Boolean

from src.extensions import db


class RecruitmentUploadedFile(db.Model):
    __tablename__ = "recruitment_uploaded_files"

    __table_args__ = (
        Index(
            "ix_recruitment_uploaded_files_application_active_cv",
            "application_id",
            "is_cv",
            "is_active",
        ),
    )

    id = Column(Integer, primary_key=True)

    application_id = Column(
        Integer,
        ForeignKey("recruitment_applications.id"),
        nullable=False,
        index=True,
    )

    original_filename = Column(String(500), nullable=False)
    content_type = Column(String(255), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    storage_provider = Column(String(50), nullable=False, default="local")
    storage_key = Column(String(1000), nullable=False)
    public_url = Column(String(1000), nullable=True)
    checksum = Column(String(255), nullable=True)
    is_cv = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    uploaded_at = Column(BigInteger)
    replaced_at = Column(BigInteger, nullable=True)
    application = db.relationship(
        "RecruitmentApplication",
        back_populates="uploaded_files",
    )

    def __init__(self, **kwargs):
        super(RecruitmentUploadedFile, self).__init__(**kwargs)
        if not self.uploaded_at:
            self.uploaded_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "storage_provider": self.storage_provider,
            "storage_key": self.storage_key,
            "public_url": self.public_url,
            "checksum": self.checksum,
            "is_cv": bool(self.is_cv),
            "is_active": bool(self.is_active),
            "version": self.version,
            "uploaded_at": self.uploaded_at,
            "replaced_at": self.replaced_at,
        }
