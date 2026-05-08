import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.hotspot_monitor import KeywordCreateRequest


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_keyword_service.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_keyword_service", SERVICE_PATH)
svc_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
HotspotKeywordService = svc_module.HotspotKeywordService


class FakeDB:
    def __init__(self, rows=None, last_id=1):
        self._rows = rows or []
        self._last_id = last_id
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((query, values))
        return self._last_id

    async def fetch_all(self, query, values=None):
        return self._rows

    async def fetch_one(self, query, values=None):
        return self._rows[0] if self._rows else None


def test_create_keyword_returns_id():
    async def run():
        db = FakeDB(last_id=42)
        svc = HotspotKeywordService(db)
        result = await svc.create_keyword(KeywordCreateRequest(text="AI编程"), user_id=1)
        assert result == 42
        assert "INSERT INTO hotspot_keyword" in db.executed[0][0]

    asyncio.run(run())


def test_list_keywords_maps_rows():
    class FakeRow:
        def __getitem__(self, key):
            data = {"id": 1, "text": "AI编程", "category": None, "isActive": 1,
                    "hotspotCount": 5, "createTime": None}
            return data[key]

    async def run():
        db = FakeDB(rows=[FakeRow()])
        svc = HotspotKeywordService(db)
        result = await svc.list_keywords(user_id=1)
        assert len(result) == 1
        assert result[0].text == "AI编程"
        assert result[0].hotspot_count == 5

    asyncio.run(run())
