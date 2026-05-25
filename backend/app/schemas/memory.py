"""Long-term memory schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    memory_type: str = Field(..., alias="memoryType", min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    weight: int = Field(default=50, ge=0, le=100)

    class Config:
        populate_by_name = True


class MemoryUpdateRequest(BaseModel):
    memory_type: Optional[str] = Field(None, alias="memoryType", min_length=1, max_length=32)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    weight: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        populate_by_name = True


class MemoryVO(BaseModel):
    id: int
    user_id: int = Field(alias="userId")
    memory_type: str = Field(alias="memoryType")
    title: str
    content: str
    weight: int
    source: str
    is_active: bool = Field(alias="isActive")
    create_time: Optional[datetime] = Field(None, alias="createTime")
    update_time: Optional[datetime] = Field(None, alias="updateTime")

    class Config:
        populate_by_name = True
