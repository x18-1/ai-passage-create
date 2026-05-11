"""Agent context snapshot ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class AgentContextSnapshot(Base):
    """Prompt context injected into an Agent stage."""

    __tablename__ = "agent_context_snapshot"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column("taskId", String(64), nullable=False)
    user_id = Column("userId", BigInteger, nullable=False)
    stage = Column(String(32), nullable=False)
    memory_context = Column("memoryContext", Text, nullable=True)
    skill_context = Column("skillContext", Text, nullable=True)
    rag_context = Column("ragContext", Text, nullable=True)
    hotspot_context = Column("hotspotContext", Text, nullable=True)
    article_example_context = Column("articleExampleContext", Text, nullable=True)
    token_estimate = Column("tokenEstimate", Integer, nullable=False, default=0)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
