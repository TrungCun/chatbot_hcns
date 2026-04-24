from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Tên vị trí tuyển dụng")
    department: str = Field(..., min_length=1, max_length=100, description="Phòng ban")
    description: str = Field(..., min_length=1, description="Mô tả công việc")
    requirements: str = Field(..., min_length=1, description="Yêu cầu ứng viên")
    salary_range: Optional[str] = Field(default=None, max_length=100, description="Khoảng lương (VD: 10-20 triệu)")
    location: str = Field(..., min_length=1, max_length=200, description="Địa điểm làm việc")
    slots: int = Field(default=1, ge=1, description="Số lượng cần tuyển")


class JobUpdate(BaseModel):
    """Schema cập nhật vị trí tuyển dụng (tất cả field đều optional)."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    department: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, min_length=1)
    requirements: Optional[str] = Field(default=None, min_length=1)
    salary_range: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, min_length=1, max_length=200)
    slots: Optional[int] = Field(default=None, ge=1)
    status: Optional[Literal["open", "closed"]] = None


class JobResponse(BaseModel):
    id: str = Field(..., description="ID duy nhất của vị trí")
    title: str
    department: str
    description: str
    requirements: str
    salary_range: Optional[str]
    location: str
    slots: int
    status: Literal["open", "closed"] = Field(..., description="Trạng thái tuyển dụng")
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    total: int
    items: list[JobResponse]
