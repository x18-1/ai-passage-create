"""Knowledge base schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


KnowledgeSourceType = Literal["upload", "article", "hotspot", "system"]


class KnowledgeDocumentVO(BaseModel):
    id: int
    user_id: int = Field(alias="userId")
    title: str
    source_type: str = Field(alias="sourceType")
    source_id: Optional[str] = Field(None, alias="sourceId")
    collection_name: str = Field(alias="collectionName")
    status: str
    chunk_count: int = Field(alias="chunkCount")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    create_time: Optional[datetime] = Field(None, alias="createTime")
    update_time: Optional[datetime] = Field(None, alias="updateTime")

    class Config:
        populate_by_name = True


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collections: list[str] = Field(default_factory=list)
    top_k: int = Field(5, alias="topK", ge=1, le=20)

    class Config:
        populate_by_name = True


class KnowledgeQueryResultVO(BaseModel):
    text: str
    source: str
    score: float
    title: Optional[str] = None
