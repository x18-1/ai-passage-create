"""文章草稿同步记录服务"""

from datetime import datetime
from typing import List

from app.exceptions import ErrorCode, throw_if_not
from app.schemas.article_sync import ArticleSyncRecordUpsertRequest, ArticleSyncRecordVO
from app.schemas.user import LoginUserVO


class ArticleSyncRecordService:
    """文章草稿同步记录服务"""

    def __init__(self, db):
        self.db = db

    async def upsert_record(self, request: ArticleSyncRecordUpsertRequest, login_user: LoginUserVO) -> bool:
        """按 taskId + userId + platform 创建或更新草稿同步记录"""
        await self._check_article_permission(request.task_id, login_user)
        now = datetime.now()
        await self.db.execute(
            query="""
                INSERT INTO article_sync_record (
                    taskId, userId, platform, platformName, status, draftLink, errorMessage, lastSyncTime, createTime, updateTime
                )
                VALUES (
                    :taskId, :userId, :platform, :platformName, :status, :draftLink, :errorMessage, :lastSyncTime, :createTime, :updateTime
                )
                ON DUPLICATE KEY UPDATE
                    platformName = VALUES(platformName),
                    status = VALUES(status),
                    draftLink = VALUES(draftLink),
                    errorMessage = VALUES(errorMessage),
                    lastSyncTime = VALUES(lastSyncTime),
                    updateTime = VALUES(updateTime),
                    isDelete = 0
            """,
            values={
                "taskId": request.task_id,
                "userId": login_user.id,
                "platform": request.platform,
                "platformName": request.platform_name,
                "status": request.status,
                "draftLink": request.draft_link,
                "errorMessage": request.error_message,
                "lastSyncTime": now,
                "createTime": now,
                "updateTime": now,
            },
        )
        return True

    async def list_records(self, task_id: str, login_user: LoginUserVO) -> List[ArticleSyncRecordVO]:
        """查询当前用户某篇文章的草稿同步记录"""
        await self._check_article_permission(task_id, login_user)
        rows = await self.db.fetch_all(
            query="""
                SELECT
                    id, taskId, userId, platform, platformName, status, draftLink, errorMessage,
                    lastSyncTime, createTime, updateTime
                FROM article_sync_record
                WHERE taskId = :taskId AND userId = :userId AND isDelete = 0
                ORDER BY updateTime DESC
            """,
            values={"taskId": task_id, "userId": login_user.id},
        )
        return [self._to_vo(row) for row in rows]

    async def _check_article_permission(self, task_id: str, login_user: LoginUserVO):
        row = await self.db.fetch_one(
            query="""
                SELECT userId
                FROM article
                WHERE taskId = :taskId AND isDelete = 0
            """,
            values={"taskId": task_id},
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        if login_user.user_role != "admin":
            throw_if_not(row["userId"] == login_user.id, ErrorCode.NO_AUTH_ERROR, "无权限访问该文章")

    def _to_vo(self, row) -> ArticleSyncRecordVO:
        row_dict = dict(row)
        return ArticleSyncRecordVO(
            id=row_dict["id"],
            taskId=row_dict["taskId"],
            userId=row_dict["userId"],
            platform=row_dict["platform"],
            platformName=row_dict["platformName"],
            status=row_dict["status"],
            draftLink=row_dict.get("draftLink"),
            errorMessage=row_dict.get("errorMessage"),
            lastSyncTime=row_dict["lastSyncTime"].isoformat(),
            createTime=row_dict["createTime"].isoformat(),
            updateTime=row_dict["updateTime"].isoformat(),
        )
