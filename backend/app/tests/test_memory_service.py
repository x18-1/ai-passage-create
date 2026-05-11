import asyncio
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.memory import MemoryCreateRequest


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "memory_service.py"
spec = importlib.util.spec_from_file_location("memory_service", SERVICE_PATH)
svc_module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
MemoryService = svc_module.MemoryService


class FakeRow(dict):
    def __getattr__(self, key):
        return self[key]


class FakeDB:
    def __init__(self, rows=None, last_id=1):
        self.rows = rows or []
        self.last_id = last_id
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((str(query), values or {}))
        return self.last_id

    async def fetch_all(self, query, values=None):
        self.executed.append((str(query), values or {}))
        return self.rows

    async def fetch_one(self, query, values=None):
        self.executed.append((str(query), values or {}))
        return self.rows[0] if self.rows else None


class LoginUser:
    id = 7


def test_create_memory_inserts_manual_active_memory():
    async def run():
        db = FakeDB(last_id=42)
        service = MemoryService(db)
        result = await service.create_memory(
            MemoryCreateRequest(
                memoryType="style",
                title="少营销语",
                content="表达克制，减少夸张形容词",
                weight=80,
            ),
            LoginUser(),
        )

        assert result == 42
        query, values = db.executed[0]
        assert "INSERT INTO user_memory" in query
        assert values["userId"] == 7
        assert values["memoryType"] == "style"
        assert values["weight"] == 80

    asyncio.run(run())


def test_list_for_stage_returns_active_matching_memory_types_only():
    async def run():
        db = FakeDB(rows=[
            FakeRow({
                "id": 1,
                "userId": 7,
                "memoryType": "style",
                "title": "风格",
                "content": "少营销语",
                "weight": 80,
                "source": "manual",
                "isActive": 1,
                "createTime": None,
                "updateTime": None,
            }),
            FakeRow({
                "id": 2,
                "userId": 7,
                "memoryType": "visual",
                "title": "视觉",
                "content": "多用流程图",
                "weight": 70,
                "source": "manual",
                "isActive": 1,
                "createTime": None,
                "updateTime": None,
            }),
            FakeRow({
                "id": 3,
                "userId": 7,
                "memoryType": "constraint",
                "title": "关闭",
                "content": "不用英文",
                "weight": 50,
                "source": "manual",
                "isActive": 0,
                "createTime": None,
                "updateTime": None,
            }),
        ])
        service = MemoryService(db)

        result = await service.list_for_stage(user_id=7, stage="content")

        assert [item.id for item in result] == [1]
        assert result[0].title == "风格"

    asyncio.run(run())


def test_toggle_memory_flips_user_owned_memory():
    async def run():
        db = FakeDB(rows=[FakeRow({"id": 1, "isActive": 1})])
        service = MemoryService(db)

        result = await service.toggle_memory(memory_id=1, user_id=7)

        assert result is False
        query, values = db.executed[-1]
        assert "UPDATE user_memory" in query
        assert values["isActive"] == 0
        assert values["userId"] == 7

    asyncio.run(run())
