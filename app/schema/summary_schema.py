from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class ProfessionalEvidence(BaseModel):
    period: Optional[str] = Field(
        default=None,
        description="Khoảng thời gian làm việc hoặc thực hiện dự án. VD: '07/2024 - 12/2024'"
    )
    entity_name: Optional[str] = Field(
        default=None,
        description="Tên công ty, tổ chức hoặc tên dự án."
    )
    role: Optional[str] = Field(
        default=None,
        description="Chức danh hoặc vai trò đảm nhận. VD: 'Stock Broker', 'Thành viên'"
    )
    context_and_tasks: Optional[str] = Field(
        default=None,
        description="Tóm tắt ngắn gọn bối cảnh bài toán và các nhiệm vụ chính đã thực hiện."
    )
    skills_applied: List[str] = Field(
        default_factory=list,
        description="Các kỹ năng, công nghệ hoặc phần mềm thực tế đã sử dụng trong dự án/công việc này."
    )
    quantifiable_results: Optional[str] = Field(
        default=None,
        description="Kết quả đạt được có chứa con số định lượng. VD: 'Tăng 20% doanh thu', 'Quản lý nhóm 500+ người'."
    )

# 2. CÁC KHỐI THÔNG TIN VỆ TINH
class CandidateOverview(BaseModel):
    full_name: Optional[str] = Field(default=None, description="Họ và tên đầy đủ của ứng viên.")
    contact_info: Optional[str] = Field(default=None, description="Email, số điện thoại, link profile.")
    current_title: Optional[str] = Field(default=None, description="Chức danh hiện tại hoặc vị trí ứng tuyển.")
    total_yoe: float = Field(default=0.0, description="Tổng số năm kinh nghiệm làm việc thực tế tính ra số thập phân. VD: 1.5, 3.0.")
    inferred_domain: Optional[str] = Field(
        default=None,
        description="Tự động phân loại ngành nghề dựa trên CV. VD: 'IT/Software', 'Sales', 'Marketing', 'Hardware Engineering'."
    )

class EducationAndLanguages(BaseModel):
    institutions: List[str] = Field(default_factory=list, description="Tên các trường Đại học, Cao đẳng, Học viện.")
    highest_degree: Optional[str] = Field(default=None, description="Bằng cấp cao nhất. VD: 'Cử nhân', 'Kỹ sư'.")
    majors: List[str] = Field(default_factory=list, description="Chuyên ngành học.")
    languages: List[str] = Field(default_factory=list, description="Ngoại ngữ và chứng chỉ đi kèm. VD: 'IELTS 6.0'.")
    certifications: List[str] = Field(default_factory=list, description="Các chứng chỉ chuyên môn khác.")

class CompetencyFramework(BaseModel):
    core_skills: List[str] = Field(
        default_factory=list,
        description="Từ khóa kỹ năng chuyên môn cứng (Hard skills). Không lấy kỹ năng mềm."
    )
    tools_and_software: List[str] = Field(
        default_factory=list,
        description="Từ khóa phần mềm, công cụ hỗ trợ."
    )
    domain_knowledge: List[str] = Field(
        default_factory=list,
        description="Từ khóa kiến thức chuyên ngành. VD: 'Thị trường chứng khoán', 'Logistics'."
    )

class EvaluatorInsights(BaseModel):
    estimated_seniority: Optional[str] = Field(
        default=None,
        description="Ước lượng cấp độ chuyên môn: 'Intern/Fresher', 'Junior', 'Mid-level', 'Senior', 'Expert'."
    )
    logic_and_cv_gaps: List[str] = Field(
        default_factory=list,
        description="Các điểm bất hợp lý trong CV cần HR lưu ý. VD: Khoảng trống thời gian, thiếu số liệu chứng minh."
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Các thông tin quan trọng chưa được đề cập để hệ thống có thể chủ động hỏi thêm."
    )

# 3. ROOT TEMPLATE
class CVTemplate(BaseModel):
    candidate_overview: CandidateOverview = Field(default_factory=CandidateOverview)
    education_and_languages: EducationAndLanguages = Field(default_factory=EducationAndLanguages)
    competency_framework: CompetencyFramework = Field(default_factory=CompetencyFramework)
    professional_evidence: List[ProfessionalEvidence] = Field(default_factory=list)
    evaluator_insights: EvaluatorInsights = Field(default_factory=EvaluatorInsights)