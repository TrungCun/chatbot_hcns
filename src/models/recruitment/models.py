from src.extensions import db
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    VARCHAR,
    Date,
    BigInteger,
    Text,
    Float,
)
from datetime import date, datetime


class Company(db.Model):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    tax_code = Column(VARCHAR(50), nullable=False)
    parent_id = Column(Integer, ForeignKey("companies.id"))
    created_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, default=None)

    def __init__(self, name, tax_code, parent_id, created_at):
        self.name = name
        self.tax_code = tax_code
        self.parent_id = parent_id
        self.created_at = created_at


class Position(db.Model):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(VARCHAR(50), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("positions.id"))
    level = Column(Integer, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, default=None)

    def __init__(self, name, code, parent_id, level, created_at):
        self.name = name
        self.code = code
        self.parent_id = parent_id
        self.level = level
        self.created_at = created_at


class Department(db.Model):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey(Company.id), nullable=False)
    parent_id = Column(Integer, ForeignKey("departments.id"))
    name = Column(String(100), nullable=False)
    code = Column(VARCHAR(50), unique=True, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, default=None)

    def __init__(self, company_id, name, code, parent_id, created_at):
        self.company_id = company_id
        self.name = name
        self.code = code
        self.parent_id = parent_id
        self.created_at = created_at


class JobTitle(db.Model):
    __tablename__ = "job_titles"
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey(Department.id), nullable=False)
    position_id = Column(Integer, ForeignKey(Position.id), nullable=False)
    code = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    competency_requirement = Column(Text, nullable=True)
    benefit = Column(Text, nullable=True)
    status = Column(
        Integer, nullable=False, default=0
    )  # 0=PENDING, 1=APPROVED, 2=REJECTED
    created_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, default=None)

    def __init__(self, **kwargs):
        super(JobTitle, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.now().timestamp())

    def _to_dict(self):
        return {
            "id": self.id,
            "department_id": self.department_id,
            "position_id": self.position_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "competency_requirement": self.competency_requirement,
            "benefit": self.benefit,
            "status": self.status,
            "created_at": self.created_at,
            "deleted_at": self.deleted_at,
        }

    def _check_need_approve(self):
        # Kiểm tra nếu có job approval nào đang pending liên quan đến job title này thì return True
        pending_approval = (
            db.session.query(JobTitleDescriptionApproval)
            .filter(
                JobTitleDescriptionApproval.job_title_id == self.id,
                JobTitleDescriptionApproval.status == 0,
            )
            .first()
        )
        return pending_approval is not None


class JobTitleDescriptionApproval(db.Model):
    __tablename__ = "job_title_description_approvals"

    id = Column(Integer, primary_key=True)
    job_title_id = Column(Integer, ForeignKey("job_titles.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    request_type = Column(VARCHAR(20), nullable=False)  # CREATE / UPDATE
    status = Column(
        Integer, nullable=True, default=None
    )  # 0=PENDING, 1=APPROVED, 2=REJECTED

    # Lưu trực tiếp nội dung mô tả công việc cần duyệt
    description = Column(Text, nullable=True)
    competency_requirement = Column(Text, nullable=True)
    benefit = Column(Text, nullable=True)

    reject_reason = Column(Text, nullable=True)
    requested_at = Column(BigInteger, nullable=False)
    approved_at = Column(BigInteger, nullable=True)

    def __init__(
        self,
        job_title_id,
        department_id,
        approver_id,
        request_type,
        description,
        competency_requirement,
        benefit,
        requested_at,
        requested_by=None,
        status=0,
        reject_reason=None,
        approved_at=None,
    ):
        self.job_title_id = job_title_id
        self.department_id = department_id
        self.approver_id = approver_id
        self.requested_by = requested_by
        self.request_type = request_type
        self.status = status
        self.description = description
        self.competency_requirement = competency_requirement
        self.benefit = benefit
        self.reject_reason = reject_reason
        self.requested_at = requested_at
        self.approved_at = approved_at


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(VARCHAR(100))
    password = Column(VARCHAR(100), nullable=False)
    phone = Column(VARCHAR(20))
    telegram_chat_id = Column(VARCHAR(50))
    date_of_birth = Column(BigInteger)
    avatar = Column(String(255))
    account_stutus = Column(Integer, nullable=False)

    department_id = Column(Integer, ForeignKey(Department.id))
    position_id = Column(Integer, ForeignKey(Position.id))
    job_title_id = Column(Integer, ForeignKey(JobTitle.id))

    time_created = Column(BigInteger, nullable=False)
    leave_allow = Column(Float, default=0)
    start_working = Column(BigInteger, default=None)
    salary = Column(Integer, default=None)
    code = Column(String(8))
    position_title = Column(Text)
    color = Column(String(50), default=None)
    discord_id = Column(String(50), default=None)  # Discord ID for user
    # locked_until = Column(BIGINT, default=None)
    # failed_attempts = Column(INTEGER, default=0)
    # last_failed_at = Column(BIGINT, default=None)
    # mfa_secret = Column(TEXT, default=None)  # Secret key for MFA

    def __init__(
        self,
        name,
        email,
        password,
        phone,
        telegram_chat_id,
        date_of_birth,
        avatar,
        account_stutus,
        department_id,
        position_id,
        time_created,
        leave_allow,
        start_working,
        salary,
        position_title,
        job_title_id,
    ):
        self.name = name
        self.email = email
        self.password = password
        self.phone = phone
        self.telegram_chat_id = telegram_chat_id
        self.date_of_birth = date_of_birth
        self.avatar = avatar
        self.account_stutus = account_stutus
        self.department_id = department_id
        self.position_id = position_id
        self.time_created = time_created
        self.leave_allow = leave_allow
        self.start_working = start_working
        self.salary = salary
        self.position_title = position_title
        self.job_title_id = job_title_id

    def setCode(self, code):
        self.code = code

    def setColor(self, color):
        self.color = color

    def setDiscordId(self, discord_id):
        self.discord_id = discord_id
