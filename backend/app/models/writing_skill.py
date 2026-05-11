"""Writing Skill ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String, Text
from sqlalchemy.sql import func

from app.database import Base


class WritingSkill(Base):
    """Reusable writing prompt template."""

    __tablename__ = "writing_skill"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column("userId", BigInteger, nullable=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    prompt_template = Column("promptTemplate", Text, nullable=False)
    applicable_stages = Column("applicableStages", Text, nullable=False)
    is_system = Column("isSystem", SmallInteger, nullable=False, default=0)
    is_active = Column("isActive", SmallInteger, nullable=False, default=1)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
