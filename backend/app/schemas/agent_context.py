"""Agent context schemas."""

from pydantic import BaseModel


class AgentContext(BaseModel):
    memory_context: str = ""
    skill_context: str = ""
    rag_context: str = ""
    hotspot_context: str = ""
    article_example_context: str = ""
    instruction_block: str = ""
