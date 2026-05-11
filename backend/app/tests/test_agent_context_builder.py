import asyncio
import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

for key in (
    "DB_HOST",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "REDIS_HOST",
    "SESSION_SECRET_KEY",
    "PASSWORD_SALT",
    "DASHSCOPE_API_KEY",
    "PEXELS_API_KEY",
    "TENCENT_COS_SECRET_ID",
    "TENCENT_COS_SECRET_KEY",
    "TENCENT_COS_REGION",
    "TENCENT_COS_BUCKET",
    "NANO_BANANA_API_KEY",
):
    os.environ.setdefault(key, "test")


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "agent_context_builder.py"
spec = importlib.util.spec_from_file_location("agent_context_builder", SERVICE_PATH)
svc_module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
AgentContextBuilder = svc_module.AgentContextBuilder


class FakeMemoryService:
    async def list_for_stage(self, user_id, stage):
        return [type("Memory", (), {"title": "风格", "content": "少营销语", "weight": 80})()]


class FakeSkillService:
    async def list_for_stage(self, user_id, stage, enabled_skill_refs):
        return [type("Skill", (), {"name": "科技风", "content": "用热点切入"})()]


class FakeRagService:
    async def query_prompt_context(self, user_id, query, collections, top_k=5):
        return "[资料 1]\n内容: AI 编程热点\n来源: hotspot.md\n相关度: 0.91"


class FakeDb:
    def __init__(self):
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((str(query), values or {}))
        return 1


def test_builder_includes_memory_skill_and_rag_context():
    async def run():
        db = FakeDb()
        builder = AgentContextBuilder(
            db,
            memory_service=FakeMemoryService(),
            writing_skill_service=FakeSkillService(),
            rag_knowledge_service=FakeRagService(),
        )
        ctx = await builder.build_context(
            user_id=1,
            task_id="task-1",
            stage="content",
            topic="AI 编程",
            style="tech",
            enabled_skill_refs=["system/tech-media-analysis"],
            enable_memory=True,
            enable_rag=True,
            rag_collections=[],
        )
        assert "少营销语" in ctx.instruction_block
        assert "用热点切入" in ctx.instruction_block
        assert "AI 编程热点" in ctx.instruction_block
        assert db.executed[-1][1]["stage"] == "content"

    asyncio.run(run())


def test_builder_respects_memory_and_rag_toggles():
    async def run():
        db = FakeDb()
        builder = AgentContextBuilder(
            db,
            memory_service=FakeMemoryService(),
            writing_skill_service=FakeSkillService(),
            rag_knowledge_service=FakeRagService(),
        )
        ctx = await builder.build_context(
            user_id=1,
            task_id="task-1",
            stage="content",
            topic="AI 编程",
            style=None,
            enabled_skill_refs=[],
            enable_memory=False,
            enable_rag=False,
            rag_collections=[],
        )
        assert "少营销语" not in ctx.instruction_block
        assert "AI 编程热点" not in ctx.instruction_block
        assert "用热点切入" in ctx.instruction_block

    asyncio.run(run())
