"""文章草稿同步记录模型"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ArticleSyncStatus = Literal["SYNCING", "DRAFT_CREATED", "FAILED"]


class ArticleSyncRecordUpsertRequest(BaseModel):
    """创建或更新草稿同步记录"""

    task_id: str = Field(..., alias="taskId", min_length=1)
    platform: str = Field(..., min_length=1, max_length=64)
    platform_name: str = Field(..., alias="platformName", min_length=1, max_length=100)
    status: ArticleSyncStatus
    draft_link: Optional[str] = Field(None, alias="draftLink", max_length=1024)
    error_message: Optional[str] = Field(None, alias="errorMessage")

    class Config:
        populate_by_name = True


class ArticleSyncRecordVO(BaseModel):
    """草稿同步记录视图对象"""

    id: int
    task_id: str = Field(..., alias="taskId")
    user_id: int = Field(..., alias="userId")
    platform: str
    platform_name: str = Field(..., alias="platformName")
    status: ArticleSyncStatus
    draft_link: Optional[str] = Field(None, alias="draftLink")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    last_sync_time: str = Field(..., alias="lastSyncTime")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True
