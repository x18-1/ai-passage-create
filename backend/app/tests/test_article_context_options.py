import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.article import ArticleCreateRequest, ArticleState


def test_article_create_request_accepts_context_options():
    request = ArticleCreateRequest(
        topic="AI 编程",
        enableMemory=True,
        enableRag=True,
        enabledSkillRefs=["system/tech-media-analysis", "system/xiaohongshu-seeding"],
        ragCollections=["user_1_knowledge"],
    )
    assert request.enable_memory is True
    assert request.enable_rag is True
    assert request.enabled_skill_refs == ["system/tech-media-analysis", "system/xiaohongshu-seeding"]
    assert request.rag_collections == ["user_1_knowledge"]


def test_article_state_has_context_fields():
    state = ArticleState()
    state.user_id = 1
    state.enable_memory = True
    state.enable_rag = True
    state.enabled_skill_refs = ["system/tech-media-analysis"]
    state.rag_collections = ["user_1_knowledge"]
    assert state.user_id == 1
    assert state.enabled_skill_refs == ["system/tech-media-analysis"]
