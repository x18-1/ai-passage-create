"""Markdown-backed Writing Skill service."""

from pathlib import Path
from typing import Any

import yaml

from app.schemas.writing_skill import WritingSkillVO


DEFAULT_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "writing_skills"


class WritingSkillService:
    def __init__(self, db=None, skills_root: Path | str | None = None):
        self.db = db
        self.skills_root = Path(skills_root) if skills_root else DEFAULT_SKILLS_ROOT

    def list_skills(self) -> list[WritingSkillVO]:
        skill_dir = self.skills_root / "system"
        if not skill_dir.exists():
            return []

        skills = []
        for path in sorted(skill_dir.glob("*.md")):
            skills.append(self._load_skill(path))
        return skills

    async def list_for_stage(self, user_id: int, stage: str, enabled_skill_refs: list[str]) -> list[WritingSkillVO]:
        if not enabled_skill_refs:
            return []

        selected_refs = set(enabled_skill_refs)
        return [
            skill
            for skill in self.list_skills()
            if skill.ref in selected_refs and stage in skill.applicable_stages
        ]

    def _load_skill(self, path: Path) -> WritingSkillVO:
        raw = path.read_text(encoding="utf-8")
        metadata, content = self._split_frontmatter(raw)
        skill_id = str(metadata.get("id") or path.stem)
        applicable_stages = metadata.get("applicableStages") or metadata.get("applicable_stages") or []
        if not isinstance(applicable_stages, list):
            applicable_stages = []

        return WritingSkillVO(
            ref=f"system/{skill_id}",
            id=skill_id,
            name=str(metadata.get("name") or skill_id),
            description=str(metadata.get("description") or ""),
            applicableStages=[str(stage) for stage in applicable_stages],
            content=content.strip(),
        )

    def _split_frontmatter(self, raw: str) -> tuple[dict[str, Any], str]:
        if not raw.startswith("---\n"):
            return {}, raw

        _, rest = raw.split("---\n", 1)
        if "\n---\n" not in rest:
            return {}, raw

        frontmatter, content = rest.split("\n---\n", 1)
        metadata = yaml.safe_load(frontmatter) or {}
        if not isinstance(metadata, dict):
            return {}, content
        return metadata, content
