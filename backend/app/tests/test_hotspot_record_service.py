import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.hotspot_monitor import RecordListRequest

SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_record_service.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_record_service", SERVICE_PATH)
svc_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
HotspotRecordService = svc_module.HotspotRecordService


class FakeDB:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((query, values))
        return 1

    async def fetch_all(self, query, values=None):
        return self._rows

    async def fetch_one(self, query, values=None):
        return self._rows[0] if self._rows else None


def test_list_records_returns_empty_when_no_rows():
    async def run():
        class FakeCountRow:
            def __getitem__(self, key):
                return {"cnt": 0}[key]

        db = FakeDB(rows=[FakeCountRow()])
        # Override fetch_all to return empty for the records query
        original_fetch_all = db.fetch_all
        call_count = [0]

        async def patched_fetch_all(query, values=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return []  # records
            return []

        db.fetch_all = patched_fetch_all
        svc = HotspotRecordService(db)
        req = RecordListRequest()
        result = await svc.list_records(req, user_id=1)
        assert result.records == []
        assert result.total == 0
        assert result.has_more is False

    asyncio.run(run())


def test_url_source_exists_check():
    async def run():
        class FakeRow:
            def __getitem__(self, key):
                return {"cnt": 1}[key]

        db = FakeDB(rows=[FakeRow()])
        svc = HotspotRecordService(db)
        exists = await svc.url_source_exists("https://example.com", "bing")
        assert exists is True

    asyncio.run(run())


def test_url_source_not_exists():
    async def run():
        class FakeRow:
            def __getitem__(self, key):
                return {"cnt": 0}[key]

        db = FakeDB(rows=[FakeRow()])
        svc = HotspotRecordService(db)
        exists = await svc.url_source_exists("https://new.example.com", "bing")
        assert exists is False

    asyncio.run(run())
