"""文章草稿同步记录 ORM 模型"""

from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String, Text
from sqlalchemy.sql import func

from app.database import Base


class ArticleSyncRecord(Base):
    """文章草稿同步记录表"""

    __tablename__ = "article_sync_record"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    task_id = Column("taskId", String(64), nullable=False, comment="文章任务ID")
    user_id = Column("userId", BigInteger, nullable=False, comment="用户ID")
    platform = Column(String(64), nullable=False, comment="平台ID")
    platform_name = Column("platformName", String(100), nullable=False, comment="平台名称")
    status = Column(String(32), nullable=False, comment="状态：SYNCING/DRAFT_CREATED/FAILED")
    draft_link = Column("draftLink", String(1024), nullable=True, comment="草稿链接")
    error_message = Column("errorMessage", Text, nullable=True, comment="错误信息")
    last_sync_time = Column("lastSyncTime", DateTime, nullable=False, default=func.now(), comment="最后同步时间")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
