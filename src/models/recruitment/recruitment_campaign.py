from src.extensions import db

from src.models.recruitment.models import Department, JobTitle, User

from sqlalchemy.dialects.mssql import (
    INTEGER,
    NVARCHAR,
    TEXT,
    BIGINT,
    VARCHAR,
)
from sqlalchemy import Column, ForeignKey, Boolean, Enum, JSON, Date
from datetime import datetime
import enum

class StaffingQuotaStatus(enum.IntEnum):
    PENDING_APPROVAL = 1
    ACTIVE = 2
    SUSPENDED = 3


class ChangeRequestStatus(enum.Enum):
    PENDING = 1
    APPROVED = 2
    REJECTED = 3


class StaffingQuotaChangeRequestType(enum.Enum):
    UPDATE = "UPDATE"
    SUSPEND = "SUSPEND"
    APPLY = "APPLY"


class StaffingQuota(db.Model):
    __tablename__ = "staffing_quota"

    id = Column(INTEGER, primary_key=True)
    department_id = Column(INTEGER, ForeignKey(Department.id), nullable=False)
    jobtitle_id = Column(INTEGER, ForeignKey(JobTitle.id), nullable=False)
    quota_number = Column(INTEGER, default=1, nullable=False) # Định biên số lượng nhân sự cho một vị trí công việc trong một phòng ban
    status = Column(INTEGER, default=StaffingQuotaStatus.ACTIVE.value) # Trạng thái của định biên: 1 - Chờ duyệt, 2 - Đang áp dụng, 3 - Tạm ngưng
    effective_date = Column(Date) # Ngày hiệu lực của định biên
    created_by = Column(INTEGER, ForeignKey(User.id))
    created_at = Column(BIGINT)
    updated_at = Column(BIGINT)

    @property
    def shortage_surplus(self):
        """
        Thiếu/Dư = Số lượng hiện có - Số lượng định biên
        < 0 → Thiếu
        = 0 → Đủ
        > 0 → Dư
        """
        return (self.current_count or 0) - self.quota_number

    def __init__(self, department_id, jobtitle_id, quota_number, status = None, created_by=None, effective_date=None, created_at=None, updated_at=None):
        self.department_id = department_id
        self.jobtitle_id = jobtitle_id
        self.quota_number = quota_number
        self.status = status
        self.created_by = created_by
        self.effective_date = effective_date
        self.created_at = created_at or int(datetime.now().timestamp())
        self.updated_at = updated_at

    def to_dict(self):
        return {
            "id": self.id,
            "department_id": self.department_id,
            "jobtitle_id": self.jobtitle_id,
            "quota_number": self.quota_number,
            "status": self.status.value if isinstance(self.status, StaffingQuotaStatus) else self.status,
            # "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class StaffingQuotaChangeRequest(db.Model):
    __tablename__ = "staffing_quota_change_requests"

    id = Column(INTEGER, primary_key=True)
    quota_id = Column(INTEGER, ForeignKey(StaffingQuota.id), nullable=False)
    change_type = Column(VARCHAR(20), nullable=False, default=StaffingQuotaChangeRequestType.UPDATE.value)
    old_quota_number = Column(INTEGER)
    new_quota_number = Column(INTEGER)
    requested_by = Column(INTEGER, ForeignKey(User.id))
    approved_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    status = Column(INTEGER, default=ChangeRequestStatus.PENDING.value)  # 1 - Pending, 2 - Approved, 3 - Rejected
    reason = Column(TEXT, nullable=True)
    related_recruitment_request_id = Column(INTEGER, nullable=True)
    created_at = Column(BIGINT)

    def __init__(self, quota_id, old_quota_number, new_quota_number, requested_by, reason=None, related_recruitment_request_id=None, status=ChangeRequestStatus.PENDING.value, created_at=None, change_type=StaffingQuotaChangeRequestType.UPDATE.value):
        self.quota_id = quota_id
        self.change_type = change_type
        self.old_quota_number = old_quota_number
        self.new_quota_number = new_quota_number
        self.requested_by = requested_by
        self.reason = reason
        self.related_recruitment_request_id = related_recruitment_request_id
        self.status = status
        self.created_at = created_at or int(datetime.now().timestamp())
        
    def to_dict(self):
        return {
            "id": self.id,
            "quota_id": self.quota_id,
            "change_type": self.change_type,
            "old_quota_number": self.old_quota_number,
            "new_quota_number": self.new_quota_number,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "status": self.status,
            "reason": self.reason,
            "related_recruitment_request_id": self.related_recruitment_request_id,
            # "created_at": self.created_at.isoformat() if self.created_at else None,
            # "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StaffingQuotaAuditLog(db.Model):
    __tablename__ = "staffing_quota_audit_logs"

    id = Column(INTEGER, primary_key=True)
    quota_id = Column(INTEGER, ForeignKey("staffing_quota.id"))
    action_type = Column(VARCHAR(100), nullable=False)
    performed_by = Column(INTEGER, ForeignKey(User.id))
    performed_at = Column(BIGINT)
    quota_before = Column(JSON, nullable=True)
    quota_after = Column(JSON, nullable=True)
    reason = Column(TEXT, nullable=True)
    related_recruitment_request_id = Column(INTEGER, nullable=True)

    def __init__(self, quota_id, action_type, performed_by, quota_before=None, quota_after=None, reason=None, related_recruitment_request_id=None, performed_at=None):
        self.quota_id = quota_id
        self.action_type = action_type
        self.performed_by = performed_by
        self.quota_before = quota_before
        self.quota_after = quota_after
        self.reason = reason
        self.related_recruitment_request_id = related_recruitment_request_id
        self.performed_at = performed_at or int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "quota_id": self.quota_id,
            "action_type": self.action_type,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at.isoformat() if self.performed_at else None,
            "quota_before": self.quota_before,
            "quota_after": self.quota_after,
            "reason": self.reason,
            "related_recruitment_request_id": self.related_recruitment_request_id,
        }


class RecruitmentCVSource(db.Model):
    __tablename__ = "recruitment_cv_sources"

    id = Column(INTEGER, primary_key=True)
    name = Column(NVARCHAR(255), nullable=False)
    description = Column(TEXT)
    created_at = Column(BIGINT)

    def __init__(self, name, description=None, created_at=None):
        self.name = name
        self.description = description
        self.created_at = created_at or int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at
        }


class RecruitmentCandidate(db.Model):
    __tablename__ = "recruitment_candidates"

    id = Column(INTEGER, primary_key=True)
    name = Column(NVARCHAR(100), nullable=False)
    email = Column(NVARCHAR(100), nullable=False)
    phone = Column(NVARCHAR(100), nullable=False)
    birthday = Column(BIGINT)
    gender = Column(INTEGER)     # 1: Nam, 2: Nữ, 0: Khác
    address = Column(NVARCHAR(255))
    education_level = Column(INTEGER)
    experience_years = Column(INTEGER)
    current_salary = Column(INTEGER)
    expected_salary = Column(INTEGER)
    source_id = Column(INTEGER, ForeignKey("recruitment_cv_sources.id"))
    overall_status = Column(INTEGER, default=1)  # 1: Chưa phân loại, ...
    create_at = Column(BIGINT)
    updated_at = Column(BIGINT)
    description = Column(TEXT)

    chat_sessions = db.relationship(
        "RecruitmentChatSession",
        back_populates="candidate",
    )

    def __init__(self, **kwargs):
        super(RecruitmentCandidate, self).__init__(**kwargs)
        if not self.create_at:
            self.create_at = int(datetime.now().timestamp())
        if not self.updated_at:
            self.updated_at = self.create_at

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "birthday": self.birthday,
            "gender": self.gender,
            "address": self.address,
            "education_level": self.education_level,
            "experience_years": self.experience_years,
            "current_salary": self.current_salary,
            "expected_salary": self.expected_salary,
            "source_id": self.source_id,
            "overall_status": self.overall_status,
            "create_at": self.create_at,
            "updated_at": self.updated_at,
            "description": self.description
        }


class RecruitmentCandidateCV(db.Model):
    """Lưu trữ file CV của ứng viên; mỗi ứng viên chỉ có một CV duy nhất (quan hệ 1-1)."""
    __tablename__ = "recruitment_candidate_cvs"

    id = Column(INTEGER, primary_key=True)
    candidate_id = Column(INTEGER, ForeignKey("recruitment_candidates.id"), nullable=False)
    cv_file = Column(NVARCHAR(255), nullable=False)       # tên file lưu trên đĩa
    cv_path = Column(NVARCHAR(500), nullable=True)        # đường dẫn đầy đủ tới file trên đĩa
    original_name = Column(NVARCHAR(255))                 # tên file gốc do người dùng upload
    is_primary = Column(Boolean, default=False)           # CV hiệu lực / chính
    uploaded_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    uploaded_at = Column(BIGINT)
    note = Column(TEXT, nullable=True)                    # ghi chú cho phiên bản CV này

    def __init__(self, **kwargs):
        super(RecruitmentCandidateCV, self).__init__(**kwargs)
        if not self.uploaded_at:
            self.uploaded_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "cv_file": self.cv_file,
            "cv_path": self.cv_path,
            "original_name": self.original_name,
            "is_primary": bool(self.is_primary),
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at,
            "note": self.note,
        }


class RecruitmentCandidateCampaign(db.Model):
    __tablename__ = "recruitment_candidate_campaigns"

    id = Column(INTEGER, primary_key=True)
    candidate_id = Column(INTEGER, ForeignKey("recruitment_candidates.id"), nullable=False)
    campaign_id = Column(INTEGER, ForeignKey("recruitment_campaigns.id"), nullable=False)
    proposed_salary = Column(NVARCHAR(255))
    status = Column(INTEGER, default=1) # Lấy theo config, là trạng thái chung của ứng viên
    start_date = Column(BIGINT)
    probation_period = Column(INTEGER, nullable=True)               # Số tháng thử việc
    offer_approval_status = Column(INTEGER, default=1)  # pending | approved | rejected
    offer_approved_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    offer_rejection_reason = Column(TEXT, nullable=True)            # Lý do từ chối offer
    is_matching = Column(Boolean, default=False) # Cờ đánh dấu có phải ứng viên phù hợp với JD hay không (FE gửi lên)
    assigned_at = Column(BIGINT)
    assigned_by = Column(INTEGER, ForeignKey(User.id))
    updated_at = Column(BIGINT)

    def __init__(self, **kwargs):
        super(RecruitmentCandidateCampaign, self).__init__(**kwargs)
        if not self.assigned_at:
            self.assigned_at = int(datetime.now().timestamp())
        if not self.updated_at:
            self.updated_at = self.assigned_at

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "campaign_id": self.campaign_id,
            "proposed_salary": self.proposed_salary,
            "status": self.status,
            "start_date": self.start_date,
            "probation_period": self.probation_period,
            "offer_approval_status": self.offer_approval_status,
            "offer_approved_by": self.offer_approved_by,
            "offer_rejection_reason": self.offer_rejection_reason,
            "is_matching": self.is_matching,
            "assigned_at": self.assigned_at,
            "assigned_by": self.assigned_by,
            "updated_at": self.updated_at,
        }


class RecruitmentCandidateStatusHistory(db.Model):
    __tablename__ = "recruitment_candidate_status_histories"

    id = Column(INTEGER, primary_key=True)
    candidate_id = Column(INTEGER, ForeignKey("recruitment_candidates.id"), nullable=False)
    campaign_id = Column(INTEGER, ForeignKey("recruitment_campaigns.id"), nullable=True)
    old_status = Column(INTEGER)
    new_status = Column(INTEGER)
    note = Column(TEXT)
    changed_by = Column(INTEGER, ForeignKey(User.id))
    changed_at = Column(BIGINT)

    def __init__(self, candidate_id, old_status, new_status, changed_by,
                 note=None, campaign_id=None, changed_at=None):
        self.candidate_id = candidate_id
        self.old_status = old_status
        self.new_status = new_status
        self.changed_by = changed_by
        self.note = note
        self.campaign_id = campaign_id
        self.changed_at = changed_at or int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "campaign_id": self.campaign_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "note": self.note,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at
        }


class RecruitmentRequest(db.Model):
    __tablename__ = "recruitment_requests"

    id = Column(INTEGER, primary_key=True)
    department_id = Column(INTEGER, ForeignKey(Department.id), nullable=False)
    jobtitle_id = Column(INTEGER, ForeignKey(JobTitle.id), nullable=False)
    jobtitle_detail = Column(TEXT)
    name = Column(NVARCHAR(255), nullable=True)
    quantity = Column(INTEGER, nullable=False)
    gender = Column(INTEGER)
    deadline = Column(BIGINT)
    salary_range = Column(NVARCHAR(255))
    need_type = Column(INTEGER) 
    replacement_type = Column(INTEGER)
    replaced_user_id = Column(INTEGER, ForeignKey(User.id), nullable=True)
    replacement_reason = Column(TEXT)
    experience_level = Column(INTEGER) 
    education_level = Column(INTEGER) 
    competency_requirements = Column(TEXT)
    appearance_requirements = Column(Boolean, default=False) # Yêu cầu về ngoại hình (có/không)
    job_description = Column(TEXT)
    recruitment_reason = Column(TEXT)
    status = Column(INTEGER, default=1)
    status_name = Column(NVARCHAR(255))
    created_by = Column(INTEGER, ForeignKey(User.id))
    approved_by = Column(INTEGER, ForeignKey(User.id))
    approval_date = Column(BIGINT)
    rejected_reason = Column(TEXT)
    cancelled_reason = Column(TEXT)
    created_at = Column(BIGINT)
    updated_at = Column(BIGINT)

    def __init__(self, **kwargs):
        super(RecruitmentRequest, self).__init__(**kwargs)
        # FIX: Convert string boolean to actual boolean
        if 'appearance_requirements' in kwargs:
            val = kwargs['appearance_requirements']
            if isinstance(val, str):
                kwargs['appearance_requirements'] = val.lower() in ('true', '1', 'yes')
            self.appearance_requirements = kwargs['appearance_requirements']
        
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def check_over_quota(self, session):
        """Kiểm tra xem đề xuất này có vượt định biên hay không."""
        quota = session.query(StaffingQuota).filter_by(
            department_id=self.department_id,
            jobtitle_id=self.jobtitle_id,
            status=StaffingQuotaStatus.ACTIVE.value
        ).first()
        if not quota:
            return False  # Không có định biên nào, coi như không vượt
        
        current_count = session.query(User).filter_by(
            department_id=self.department_id,
            job_title_id=self.jobtitle_id,
            account_stutus=1  # Chỉ tính nhân sự đang hoạt động
        ).count()
        
        return (current_count + self.quantity) > quota.quota_number
    
    def check_has_campaign(self, session):
        """Kiểm tra xem đề xuất này đã có chiến dịch nào được tạo hay chưa."""
        campaign = session.query(RecruitmentCampaign).filter_by(request_id=self.id).first()
        return campaign.id if campaign else None

    def to_dict(self):
        return {
            "id": self.id,
            "department_id": self.department_id,
            "jobtitle_id": self.jobtitle_id,
            "jobtitle_detail": self.jobtitle_detail,
            "name": self.name,
            "quantity": self.quantity,
            "gender": self.gender,
            "deadline": self.deadline,
            "salary_range": self.salary_range,
            "need_type": self.need_type,
            "replacement_type": self.replacement_type,
            "replaced_user_id": self.replaced_user_id,
            "replacement_reason": self.replacement_reason,
            "experience_level": self.experience_level,
            "education_level": self.education_level,
            "competency_requirements": self.competency_requirements,
            "appearance_requirements": self.appearance_requirements,
            "job_description": self.job_description,
            "recruitment_reason": self.recruitment_reason,
            "status": self.status,
            "status_name": self.status_name,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date,
            "rejected_reason": self.rejected_reason,
            "cancelled_reason": self.cancelled_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "campaign_id": getattr(self, "campaign_id", None),
            "is_over_quota": getattr(self, "is_over_quota", None)
        }


class RecruitmentRequestApprovalStepStatus(enum.IntEnum):
    PENDING = 1
    APPROVED = 2
    REJECTED = 3
    CANCELLED = 4


class RecruitmentRequestApprovalStep(db.Model):
    __tablename__ = "recruitment_request_approval_steps"

    id = Column(INTEGER, primary_key=True)
    request_id = Column(INTEGER, ForeignKey("recruitment_requests.id"), nullable=False)
    step_order = Column(INTEGER, nullable=False)
    step_code = Column(VARCHAR(50), nullable=False) 
    position_code = Column(VARCHAR(50), nullable=False)
    department_code = Column(VARCHAR(50), nullable=True)
    status = Column(INTEGER, default=RecruitmentRequestApprovalStepStatus.PENDING.value)
    acted_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    acted_at = Column(BIGINT, nullable=True)
    rejection_reason = Column(TEXT, nullable=True)
    created_at = Column(BIGINT)
    updated_at = Column(BIGINT)

    def __init__(self, **kwargs):
        super(RecruitmentRequestApprovalStep, self).__init__(**kwargs)
        now_ts = int(datetime.now().timestamp())
        if not self.created_at:
            self.created_at = now_ts
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "step_order": self.step_order,
            "step_code": self.step_code,
            "position_code": self.position_code,
            "department_code": self.department_code,
            "status": self.status,
            "acted_by": self.acted_by,
            "acted_by_name": User.query.filter_by(id=self.acted_by).first().name if self.acted_by else None,
            "acted_at": self.acted_at,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RecruitmentRequestAttachment(db.Model):
    __tablename__ = "recruitment_request_attachments"

    id = Column(INTEGER, primary_key=True)
    request_id = Column(INTEGER, ForeignKey("recruitment_requests.id"), nullable=False)
    file_name = Column(NVARCHAR(255), nullable=False)
    original_name = Column(NVARCHAR(255), nullable=False)
    file_path = Column(NVARCHAR(500), nullable=False)
    uploaded_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    uploaded_at = Column(BIGINT)

    def __init__(self, **kwargs):
        super(RecruitmentRequestAttachment, self).__init__(**kwargs)
        if not self.uploaded_at:
            self.uploaded_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "file_name": self.file_name,
            "original_name": self.original_name,
            "file_path": self.file_path,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at,
        }


class RecruitmentRequestQuestion(db.Model):
    __tablename__ = "recruitment_request_questions"

    id = Column(INTEGER, primary_key=True)
    request_id = Column(INTEGER, ForeignKey("recruitment_requests.id"), nullable=False)
    content = Column(TEXT, nullable=False)
    created_at = Column(BIGINT)

    def __init__(self, **kwargs):
        super(RecruitmentRequestQuestion, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "content": self.content,
            "created_at": self.created_at
        }


class RecruitmentCampaign(db.Model):
    __tablename__ = "recruitment_campaigns"

    id = Column(INTEGER, primary_key=True)
    request_id = Column(INTEGER, ForeignKey("recruitment_requests.id"), nullable=False)
    name = Column(NVARCHAR(255), nullable=False)
    status = Column(INTEGER, default=1) # 1=Đang triển khai, 2=Tạm dừng, 3=Bị hủy, 4=Hoàn thành
    pause_reason = Column(TEXT)
    cancel_reason = Column(TEXT)
    assignee_id = Column(INTEGER, ForeignKey(User.id))
    created_by = Column(INTEGER, ForeignKey(User.id))
    created_at = Column(BIGINT)
    updated_at = Column(BIGINT)
    start_time = Column(BIGINT, nullable=True)  # Thời gian bắt đầu chiến dịch
    end_time = Column(BIGINT, nullable=True)    # Thời gian kết thúc chiến dịch
    # JD override — chỉnh sửa khi tạo chiến dịch, không ảnh hưởng đề xuất gốc
    jd_job_description         = Column(TEXT, nullable=True)     
    jd_competency_requirements = Column(TEXT, nullable=True)
    jd_salary_range             = Column(NVARCHAR(255), nullable=True)
    jd_benefits                   = Column(TEXT, nullable=True)

    chat_sessions = db.relationship(
        "RecruitmentChatSession",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        super(RecruitmentCampaign, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "name": self.name,
            "status": self.status,
            "pause_reason": self.pause_reason,
            "cancel_reason": self.cancel_reason,
            "assignee_id": self.assignee_id,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "jd_job_description": self.jd_job_description,
            "jd_competency_requirements": self.jd_competency_requirements,
            "jd_salary_range": self.jd_salary_range,
            "jd_benefits": self.jd_benefits
        }


class RecruitmentCampaignRound(db.Model):
    __tablename__ = "recruitment_campaign_rounds"

    id = Column(INTEGER, primary_key=True)
    campaign_id = Column(INTEGER, ForeignKey("recruitment_campaigns.id"), nullable=False)
    round_number = Column(INTEGER, nullable=False)
    round_name = Column(NVARCHAR(255), nullable=False)
    created_at = Column(BIGINT)
    # Bộ câu hỏi sơ vấn template (chủ yếu dùng cho vòng Sơ vấn)
    interview_questions = Column(TEXT, nullable=True)

    def __init__(self, **kwargs):
        super(RecruitmentCampaignRound, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "round_number": self.round_number,
            "round_name": self.round_name,
            "interview_questions": self.interview_questions,
            "created_at": self.created_at
        }


class RecruitmentCampaignRoundInterviewer(db.Model):
    __tablename__ = "recruitment_campaign_round_interviewers"

    id = Column(INTEGER, primary_key=True)
    campaign_round_id = Column(INTEGER, ForeignKey("recruitment_campaign_rounds.id"), nullable=False)
    user_id = Column(INTEGER, ForeignKey(User.id), nullable=False)

    def __init__(self, campaign_round_id, user_id):
        self.campaign_round_id = campaign_round_id
        self.user_id = user_id

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_round_id": self.campaign_round_id,
            "user_id": self.user_id
        }


class CandidateCampaignRound(db.Model):
    __tablename__ = "candidate_campaign_rounds"

    id = Column(INTEGER, primary_key=True)
    campaign_id = Column(INTEGER, ForeignKey("recruitment_campaigns.id"), nullable=False)
    candidate_id = Column(INTEGER, ForeignKey("recruitment_candidates.id"), nullable=False)
    campaign_round_id = Column(INTEGER, ForeignKey("recruitment_campaign_rounds.id"), nullable=True)
    round_number = Column(INTEGER, nullable=False)
    round_name = Column(NVARCHAR(255), nullable=False)
    interview_time = Column(BIGINT)
    interview_format = Column(NVARCHAR(255))
    status = Column(INTEGER, default=1) # 1=Chờ, 2=Đã diễn ra, 3=Từ chối
    created_at = Column(BIGINT)
    # Dữ liệu sơ vấn (chủ yếu dùng cho vòng Sơ vấn)
    prescreening_note    = Column(TEXT, nullable=True)     # nhận xét chung sau sơ vấn
    prescreening_passed  = Column(Boolean, nullable=True)  # None=chưa đánh giá, True/False
    proposed_salary_gross = Column(INTEGER, nullable=True) # lương đề xuất (gross)

    def __init__(self, **kwargs):
        super(CandidateCampaignRound, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "candidate_id": self.candidate_id,
            "campaign_round_id": self.campaign_round_id,
            "round_number": self.round_number,
            "round_name": self.round_name,
            "interview_time": self.interview_time,
            "interview_format": self.interview_format,
            "status": self.status,
            "prescreening_note": self.prescreening_note,
            "prescreening_passed": self.prescreening_passed,
            "proposed_salary_gross": self.proposed_salary_gross,
            "created_at": self.created_at
        }


class CandidateCampaignRoundInterviewer(db.Model):
    __tablename__ = "candidate_campaign_round_interviewers"

    id = Column(INTEGER, primary_key=True)
    candidate_campaign_round_id = Column(INTEGER, ForeignKey("candidate_campaign_rounds.id"), nullable=False)
    user_id = Column(INTEGER, ForeignKey(User.id), nullable=False)
    review = Column(TEXT, nullable=True)  # Nhận xét của người phỏng vấn
    result = Column(INTEGER, nullable=True)  # 1=Pass, 2=Fail, 3=Hold (chỉ cho vòng khác sơ vấn)
    proposed_salary_gross = Column(INTEGER, nullable=True)  # Lương đề xuất (chỉ cho vòng khác sơ vấn)
    candidate_expected_salary = Column(INTEGER, nullable=True) # Lương ứng viên mong muốn

    def __init__(self, candidate_campaign_round_id, user_id, review=None, result=None, proposed_salary_gross=None, candidate_expected_salary=None):
        self.candidate_campaign_round_id = candidate_campaign_round_id
        self.user_id = user_id
        self.review = review
        self.result = result
        self.proposed_salary_gross = proposed_salary_gross
        self.candidate_expected_salary = candidate_expected_salary

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_campaign_round_id": self.candidate_campaign_round_id,
            "user_id": self.user_id,
            "review": self.review,
            "result": self.result,
            "proposed_salary_gross": self.proposed_salary_gross,
            "candidate_expected_salary": self.candidate_expected_salary
        }


class CandidateCampaignRoundInterviewerQuestion(db.Model):
    """Câu hỏi phỏng vấn gắn từng người PV trong vòng (snapshot + checkbox xác nhận)."""
    __tablename__ = "candidate_campaign_round_interviewer_questions"

    id = Column(INTEGER, primary_key=True)
    round_interviewer_id = Column(
        INTEGER,
        ForeignKey("candidate_campaign_round_interviewers.id"),
        nullable=False,
    )
    question_name = Column(NVARCHAR(500), nullable=False)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(BIGINT, nullable=False)
    updated_at = Column(BIGINT, nullable=True)
    deleted_at = Column(BIGINT, nullable=True)

    def __init__(self, **kwargs):
        super(CandidateCampaignRoundInterviewerQuestion, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "round_interviewer_id": self.round_interviewer_id,
            "question_name": self.question_name,
            "is_confirmed": bool(self.is_confirmed),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }


class RecruitmentCampaignAuditLog(db.Model):
    """Lưu vết hành động trên chiến dịch tuyển dụng."""
    __tablename__ = "recruitment_campaign_audit_logs"

    id = Column(INTEGER, primary_key=True)
    campaign_id = Column(INTEGER, ForeignKey("recruitment_campaigns.id"), nullable=False)
    action = Column(TEXT, nullable=False)  # Mô tả hành động bằng tiếng Việt
    performed_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    performed_at = Column(BIGINT)

    def __init__(self, campaign_id, action, performed_by, performed_at=None):
        self.campaign_id = campaign_id
        self.action = action
        self.performed_by = performed_by
        self.performed_at = performed_at or int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "action": self.action,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at,
        }


class RecruitmentCandidateCampaignAuditLog(db.Model):
    """Lưu vết hành động trên ứng viên trong chiến dịch tuyển dụng."""
    __tablename__ = "recruitment_candidate_campaign_audit_logs"

    id = Column(INTEGER, primary_key=True)
    campaign_id = Column(INTEGER, ForeignKey("recruitment_campaigns.id"), nullable=False)
    candidate_id = Column(INTEGER, ForeignKey("recruitment_candidates.id"), nullable=False)
    action = Column(TEXT, nullable=False)  # Mô tả hành động bằng tiếng Việt
    performed_by = Column(INTEGER, ForeignKey(User.id), nullable=True)
    performed_at = Column(BIGINT)

    def __init__(self, campaign_id, candidate_id, action, performed_by, performed_at=None):
        self.campaign_id = campaign_id
        self.candidate_id = candidate_id
        self.action = action
        self.performed_by = performed_by
        self.performed_at = performed_at or int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "candidate_id": self.candidate_id,
            "action": self.action,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at,
        }


class RecruitmentPlan(db.Model):
    __tablename__ = "recruitment_plans"

    id = Column(INTEGER, primary_key=True)
    plan_period_month = Column(INTEGER, nullable=False)
    plan_period_year = Column(INTEGER, nullable=False)
    file_name = Column(NVARCHAR(255), nullable=False)
    file_path = Column(NVARCHAR(500), nullable=False)
    original_name = Column(NVARCHAR(255))
    note = Column(TEXT)
    uploaded_by = Column(INTEGER, ForeignKey(User.id))
    uploaded_at = Column(BIGINT)
    def __init__(self, **kwargs):
        super(RecruitmentPlan, self).__init__(**kwargs)
        if not self.uploaded_at:
            self.uploaded_at = int(datetime.now().timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "plan_period_month": self.plan_period_month,
            "plan_period_year": self.plan_period_year,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "original_name": self.original_name,
            "note": self.note,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at
        }

