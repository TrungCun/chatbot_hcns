from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    department: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    requirements: str = Field(..., min_length=1)
    salary_range: Optional[str] = Field(default=None, max_length=100)
    location: str = Field(..., min_length=1, max_length=200)
    slots: int = Field(default=1, ge=1)

class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    department: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, min_length=1)
    requirements: Optional[str] = Field(default=None, min_length=1)
    salary_range: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, min_length=1, max_length=200)
    slots: Optional[int] = Field(default=None, ge=1)
    status: Optional[Literal["open", "closed"]] = None

class JobResponse(BaseModel):
    id: str
    title: str
    department: str
    description: str
    requirements: str
    salary_range: Optional[str]
    location: str
    slots: int
    status: Literal["open", "closed"]
    created_at: datetime
    updated_at: datetime

class JobListResponse(BaseModel):
    total: int
    items: list[JobResponse]