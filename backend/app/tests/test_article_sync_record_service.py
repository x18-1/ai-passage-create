import asyncio
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.article_sync import ArticleSyncRecordUpsertRequest
from app.schemas.user import LoginUserVO

SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "article_sync_record_service.py"
spec = importlib.util.spec_from_file_location("article_sync_record_service", SERVICE_PATH)
service_module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(service_module)
ArticleSyncRecordService = service_module.ArticleSyncRecordService


def make_user() -> LoginUserVO:
    return LoginUserVO(
        id=10,
        userAccount="tester",
        userRole="user",
        userName="tester",
        createTime="2026-05-07T12:00:00",
        updateTime="2026-05-07T12:00:00",
    )


class FakeDatabase:
    def __init__(self):
        self.executed = []
        self.article_row = {"userId": 10}
        self.records = [
            {
                "id": 1,
                "taskId": "task-1",
                "userId": 10,
                "platform": "juejin",
                "platformName": "掘金",
                "status": "DRAFT_CREATED",
                "draftLink": "https://juejin.cn/editor/drafts/1",
                "errorMessage": None,
                "lastSyncTime": datetime(2026, 5, 7, 12, 0, 0),
                "createTime": datetime(2026, 5, 7, 11, 0, 0),
                "updateTime": datetime(2026, 5, 7, 12, 0, 0),
            }
        ]

    async def fetch_one(self, query, values=None):
        if "FROM article" in str(query):
            return self.article_row
        return None

    async def execute(self, query, values=None):
        self.executed.append((str(query), values))
        return 1

    async def fetch_all(self, query, values=None):
        self.executed.append((str(query), values))
        return self.records


def test_upsert_sync_record_uses_task_platform_user_identity():
    async def run():
        db = FakeDatabase()
        service = ArticleSyncRecordService(db)
        user = make_user()

        request = ArticleSyncRecordUpsertRequest(
            taskId="task-1",
            platform="juejin",
            platformName="掘金",
            status="DRAFT_CREATED",
            draftLink="https://juejin.cn/editor/drafts/1",
        )

        result = await service.upsert_record(request, user)

        assert result is True
        _, values = db.executed[-1]
        assert values["taskId"] == "task-1"
        assert values["userId"] == 10
        assert values["platform"] == "juejin"
        assert values["status"] == "DRAFT_CREATED"
        assert values["draftLink"] == "https://juejin.cn/editor/drafts/1"

    asyncio.run(run())


def test_list_sync_records_returns_user_task_records():
    async def run():
        db = FakeDatabase()
        service = ArticleSyncRecordService(db)
        user = make_user()

        records = await service.list_records("task-1", user)

        assert len(records) == 1
        assert records[0].task_id == "task-1"
        assert records[0].platform == "juejin"
        assert records[0].status == "DRAFT_CREATED"
        assert records[0].draft_link == "https://juejin.cn/editor/drafts/1"

    asyncio.run(run())
