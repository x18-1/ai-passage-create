"""Knowledge document ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.sql import func

from app.database import Base


class KnowledgeDocument(Base):
    """Knowledge document metadata owned by the main app."""

    __tablename__ = "knowledge_document"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column("userId", BigInteger, nullable=False)
    title = Column(String(255), nullable=False)
    source_type = Column("sourceType", String(32), nullable=False)
    source_id = Column("sourceId", String(64), nullable=True)
    collection_name = Column("collectionName", String(128), nullable=False)
    file_path = Column("filePath", String(1024), nullable=True)
    status = Column(String(32), nullable=False)
    chunk_count = Column("chunkCount", Integer, nullable=False, default=0)
    error_message = Column("errorMessage", Text, nullable=True)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
