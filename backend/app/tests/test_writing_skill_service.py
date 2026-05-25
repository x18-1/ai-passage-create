import asyncio
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "writing_skill_service.py"
spec = importlib.util.spec_from_file_location("writing_skill_service", SERVICE_PATH)
svc_module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
WritingSkillService = svc_module.WritingSkillService


def write_skill(root: Path, filename: str, body: str) -> None:
    skill_dir = root / "system"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / filename).write_text(body, encoding="utf-8")


def test_list_skills_loads_markdown_frontmatter(tmp_path):
    write_skill(
        tmp_path,
        "tech-media-analysis.md",
        """---
id: tech-media-analysis
name: 科技自媒体深度分析
description: 适合公众号和知乎
applicableStages:
  - title
  - content
---

# 写作要求

- 用热点切入
""",
    )
    service = WritingSkillService(skills_root=tmp_path)

    result = service.list_skills()

    assert len(result) == 1
    assert result[0].ref == "system/tech-media-analysis"
    assert result[0].name == "科技自媒体深度分析"
    assert result[0].applicable_stages == ["title", "content"]
    assert "用热点切入" in result[0].content


def test_list_for_stage_filters_by_refs_and_stage(tmp_path):
    write_skill(
        tmp_path,
        "tech-media-analysis.md",
        """---
id: tech-media-analysis
name: 科技自媒体深度分析
applicableStages:
  - content
---
content skill
""",
    )
    write_skill(
        tmp_path,
        "visual-style.md",
        """---
id: visual-style
name: 视觉风格
applicableStages:
  - image
---
image skill
""",
    )
    service = WritingSkillService(skills_root=tmp_path)

    async def run():
        result = await service.list_for_stage(
            user_id=7,
            stage="content",
            enabled_skill_refs=["system/tech-media-analysis", "system/visual-style"],
        )
        assert [item.ref for item in result] == ["system/tech-media-analysis"]

    asyncio.run(run())
