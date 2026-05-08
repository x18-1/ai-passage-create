-- 热点监控关键词表
CREATE TABLE IF NOT EXISTS hotspot_keyword (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    userId     BIGINT NOT NULL COMMENT '所属用户 ID',
    text       VARCHAR(200) NOT NULL COMMENT '关键词',
    category   VARCHAR(100) NULL COMMENT '分类（可选）',
    isActive   TINYINT DEFAULT 1 NOT NULL COMMENT '是否激活',
    createTime DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updateTime DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_userId_text (userId, text(191)),
    INDEX idx_userId_active (userId, isActive)
) COMMENT='热点监控关键词' COLLATE=utf8mb4_unicode_ci;

-- 热点记录表
CREATE TABLE IF NOT EXISTS hotspot_record (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    userId           BIGINT NOT NULL COMMENT '所属用户 ID',
    keywordId        BIGINT NULL COMMENT '关联关键词（删除时置 NULL）',
    keywordText      VARCHAR(200) NULL COMMENT '关键词快照',
    title            VARCHAR(500) NOT NULL COMMENT '热点标题',
    content          TEXT NULL COMMENT '原始内容',
    url              VARCHAR(1024) NOT NULL COMMENT '链接',
    source           VARCHAR(50) NOT NULL COMMENT '来源',
    sourceId         VARCHAR(200) NULL COMMENT '平台内容 ID',
    isReal           TINYINT DEFAULT 1 NOT NULL COMMENT '是否真实内容',
    relevance        INT DEFAULT 0 NOT NULL COMMENT '相关性 0-100',
    relevanceReason  VARCHAR(500) NULL COMMENT '相关性理由',
    keywordMentioned TINYINT DEFAULT 0 NOT NULL COMMENT '是否直接提及关键词',
    importance       VARCHAR(20) DEFAULT 'low' NOT NULL COMMENT 'low/medium/high/urgent',
    summary          VARCHAR(500) NULL COMMENT 'AI 摘要',
    heatScore        FLOAT DEFAULT 0 NOT NULL COMMENT '热度分',
    viewCount        BIGINT NULL,
    likeCount        BIGINT NULL,
    retweetCount     BIGINT NULL,
    commentCount     BIGINT NULL,
    authorName       VARCHAR(200) NULL,
    authorUsername   VARCHAR(200) NULL,
    authorFollowers  BIGINT NULL,
    authorVerified   TINYINT NULL,
    publishedAt      DATETIME NULL COMMENT '内容发布时间',
    createTime       DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '发现时间',
    INDEX idx_userId_importance (userId, importance),
    INDEX idx_userId_createTime (userId, createTime),
    INDEX idx_keywordId (keywordId),
    UNIQUE KEY uk_url_source (url(512), source)
) COMMENT='热点记录' COLLATE=utf8mb4_unicode_ci;

-- 热点站内通知表
CREATE TABLE IF NOT EXISTS hotspot_notification (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    type            VARCHAR(50) DEFAULT 'hotspot' NOT NULL COMMENT 'hotspot/alert',
    title           VARCHAR(300) NOT NULL,
    content         VARCHAR(500) NULL,
    isRead          TINYINT DEFAULT 0 NOT NULL,
    hotspotRecordId BIGINT NULL COMMENT '关联热点记录 ID',
    createTime      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_isRead (isRead),
    INDEX idx_createTime (createTime)
) COMMENT='热点站内通知' COLLATE=utf8mb4_unicode_ci;
