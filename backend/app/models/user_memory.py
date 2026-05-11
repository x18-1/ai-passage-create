"""User memory ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.sql import func

from app.database import Base


class UserMemory(Base):
    """User long-term memory."""

    __tablename__ = "user_memory"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column("userId", BigInteger, nullable=False)
    memory_type = Column("memoryType", String(32), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    weight = Column(Integer, nullable=False, default=50)
    source = Column(String(32), nullable=False, default="manual")
    is_active = Column("isActive", SmallInteger, nullable=False, default=1)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
