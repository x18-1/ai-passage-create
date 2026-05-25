SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE ai_passage_creator;

CREATE TABLE IF NOT EXISTS user_memory (
    id bigint auto_increment primary key,
    userId bigint not null comment '用户ID',
    memoryType varchar(32) not null comment 'style/platform/topic/constraint/visual',
    title varchar(200) not null comment '记忆标题',
    content text not null comment '记忆内容',
    weight int default 50 not null comment '权重 0-100',
    source varchar(32) default 'manual' not null comment 'manual/article/system',
    isActive tinyint default 1 not null comment '是否启用',
    createTime datetime default CURRENT_TIMESTAMP not null,
    updateTime datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    isDelete tinyint default 0 not null,
    index idx_user_active (userId, isActive),
    index idx_user_type (userId, memoryType)
) comment '用户长期记忆' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_document (
    id bigint auto_increment primary key,
    userId bigint not null comment '用户ID',
    title varchar(255) not null comment '文档标题',
    sourceType varchar(32) not null comment 'upload/article/hotspot/system',
    sourceId varchar(64) null comment '来源ID',
    collectionName varchar(128) not null comment 'RAG collection',
    filePath varchar(1024) null comment '源文件路径',
    status varchar(32) not null comment 'pending/processing/ready/failed',
    chunkCount int default 0 not null comment 'chunk数量',
    errorMessage text null comment '错误信息',
    createTime datetime default CURRENT_TIMESTAMP not null,
    updateTime datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    isDelete tinyint default 0 not null,
    index idx_user_status (userId, status),
    index idx_user_source (userId, sourceType, sourceId),
    index idx_collection (collectionName)
) comment '知识库文档元数据' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_context_snapshot (
    id bigint auto_increment primary key,
    taskId varchar(64) not null comment '文章任务ID',
    userId bigint not null comment '用户ID',
    stage varchar(32) not null comment 'title/outline/content/image',
    memoryContext mediumtext null,
    skillContext mediumtext null,
    ragContext mediumtext null,
    hotspotContext mediumtext null,
    articleExampleContext mediumtext null,
    tokenEstimate int default 0 not null,
    createTime datetime default CURRENT_TIMESTAMP not null,
    index idx_task_stage (taskId, stage),
    index idx_user_time (userId, createTime)
) comment 'Agent上下文快照' collate = utf8mb4_unicode_ci;

ALTER TABLE article
    ADD COLUMN enableMemory tinyint default 1 not null comment '是否启用长期记忆',
    ADD COLUMN enableRag tinyint default 1 not null comment '是否启用RAG',
    ADD COLUMN enabledSkillRefs json null comment '启用的写作Skill引用列表',
    ADD COLUMN ragCollections json null comment '启用的RAG集合';
