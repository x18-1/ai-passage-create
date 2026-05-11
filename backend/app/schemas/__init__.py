"""Pydantic 请求/响应模型"""

from app.schemas.common import BaseResponse, PageRequest, DeleteRequest
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserAddRequest,
    UserUpdateRequest,
    UserQueryRequest,
    UserVO,
    LoginUserVO
)
from app.schemas.article import (
    ArticleCreateRequest,
    ArticleQueryRequest,
    ArticleVO,
    ArticleState,
    TitleResult,
    OutlineSection,
    OutlineResult,
    ImageRequirement,
    ImageResult,
    Agent4Result
)
from app.schemas.article_sync import ArticleSyncRecordUpsertRequest, ArticleSyncRecordVO
from app.schemas.knowledge import KnowledgeDocumentVO, KnowledgeQueryRequest, KnowledgeQueryResultVO
from app.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest, MemoryVO
from app.schemas.statistics import AgentLogVO, AgentExecutionStatsVO, StatisticsVO
from app.schemas.writing_skill import WritingSkillVO

__all__ = [
    "BaseResponse",
    "PageRequest",
    "DeleteRequest",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserAddRequest",
    "UserUpdateRequest",
    "UserQueryRequest",
    "UserVO",
    "LoginUserVO",
    "ArticleCreateRequest",
    "ArticleQueryRequest",
    "ArticleVO",
    "ArticleState",
    "TitleResult",
    "OutlineSection",
    "OutlineResult",
    "ImageRequirement",
    "ImageResult",
    "Agent4Result",
    "ArticleSyncRecordUpsertRequest",
    "ArticleSyncRecordVO",
    "KnowledgeDocumentVO",
    "KnowledgeQueryRequest",
    "KnowledgeQueryResultVO",
    "MemoryCreateRequest",
    "MemoryUpdateRequest",
    "MemoryVO",
    "AgentLogVO",
    "AgentExecutionStatsVO",
    "StatisticsVO",
    "WritingSkillVO",
]
