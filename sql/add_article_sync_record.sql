-- 文章草稿同步记录表
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE ai_passage_creator;

CREATE TABLE IF NOT EXISTS article_sync_record
(
    id              bigint auto_increment comment 'id' primary key,
    taskId          varchar(64)                         not null comment '文章任务ID',
    userId          bigint                              not null comment '用户ID',
    platform        varchar(64)                         not null comment '平台ID',
    platformName    varchar(100)                        not null comment '平台名称',
    status          varchar(32)                         not null comment '状态：SYNCING/DRAFT_CREATED/FAILED',
    draftLink       varchar(1024)                       null comment '草稿链接',
    errorMessage    text                                null comment '错误信息',
    lastSyncTime    datetime default CURRENT_TIMESTAMP  not null comment '最后同步时间',
    createTime      datetime default CURRENT_TIMESTAMP  not null comment '创建时间',
    updateTime      datetime default CURRENT_TIMESTAMP  not null on update CURRENT_TIMESTAMP comment '更新时间',
    isDelete        tinyint  default 0                  not null comment '是否删除',
    UNIQUE KEY uk_task_user_platform (taskId, userId, platform),
    INDEX idx_taskId (taskId),
    INDEX idx_userId (userId),
    INDEX idx_status (status),
    INDEX idx_updateTime (updateTime)
) comment '文章草稿同步记录表' collate = utf8mb4_unicode_ci;
