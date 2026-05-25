"""Writing Skill schemas."""

from pydantic import BaseModel, Field


class WritingSkillVO(BaseModel):
    ref: str
    id: str
    name: str
    description: str = ""
    applicable_stages: list[str] = Field(default_factory=list, alias="applicableStages")
    content: str = ""

    class Config:
        populate_by_name = True
