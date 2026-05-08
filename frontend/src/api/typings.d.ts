declare namespace API {
  type HotspotSource = 'weibo' | 'bilibili' | 'sogou' | 'bing' | 'hackernews' | 'twitter' | 'duckduckgo'

  type HotspotTopicSuggestionRequest = {
    keyword: string
    hotspots?: HotspotVO[]
    limit?: number
  }

  type HotspotRadarRequest = {
    keyword: string
    sources?: HotspotSource[]
    analyzeLimit?: number
  }

  type HotspotVO = {
    title: string
    content: string
    url: string
    source: HotspotSource
    publishedAt?: string
    heatScore: number
    isReal: boolean
    relevance: number
    relevanceReason: string
    keywordMentioned: boolean
    importance: 'low' | 'medium' | 'high' | 'urgent'
    summary: string
    viewCount?: number
    likeCount?: number
    retweetCount?: number
    commentCount?: number
    authorName?: string
  }

  type TopicSuggestionVO = {
    title: string
    contentDescription: string
    angle: string
    viralReason: string
    suitablePlatforms: string[]
    sourceHotspotTitles: string[]
  }

  type HotspotTopicSuggestionResponse = {
    keyword: string
    suggestions: TopicSuggestionVO[]
  }

  type HotspotRadarStatsVO = {
    total: number
    today: number
    urgent: number
    highRelevance: number
    sourceCount: number
  }

  type HotspotSourceFailureVO = {
    source: HotspotSource
    error: string
  }

  type HotspotDiagnosticVO = {
    level: 'info' | 'warning' | 'error'
    stage: string
    message: string
    source?: HotspotSource
    count?: number
    elapsedMs?: number
  }

  type HotspotRadarResponse = {
    keyword: string
    expandedKeywords: string[]
    stats: HotspotRadarStatsVO
    hotspots: HotspotVO[]
    failedSources: string[]
    failedSourceDetails: HotspotSourceFailureVO[]
    diagnostics: HotspotDiagnosticVO[]
  }

  type BaseResponseHotspotTopicSuggestionResponse = {
    code?: number
    data?: HotspotTopicSuggestionResponse
    message?: string
  }

  type BaseResponseHotspotRadarResponse = {
    code?: number
    data?: HotspotRadarResponse
    message?: string
  }

  type AgentExecutionStats = {
    taskId?: string
    totalDurationMs?: number
    agentCount?: number
    agentDurations?: Record<string, any>
    overallStatus?: string
    logs?: AgentLog[]
  }

  type AgentLog = {
    id?: number
    taskId?: string
    agentName?: string
    startTime?: string
    endTime?: string
    durationMs?: number
    status?: string
    errorMessage?: string
    prompt?: string
    inputData?: string
    outputData?: string
    createTime?: string
    updateTime?: string
    isDelete?: number
  }

  type ArticleAiModifyOutlineRequest = {
    taskId?: string
    modifySuggestion?: string
  }

  type ArticleConfirmOutlineRequest = {
    taskId?: string
    outline?: OutlineSection[]
  }

  type ArticleConfirmTitleRequest = {
    taskId?: string
    selectedMainTitle?: string
    selectedSubTitle?: string
    userDescription?: string
  }

  type ArticleCreateRequest = {
    topic?: string
    style?: string
    enabledImageMethods?: string[]
  }

  type ArticleQueryRequest = {
    pageNum?: number
    pageSize?: number
    sortField?: string
    sortOrder?: string
    userId?: number
    status?: string
  }

  type ArticleSyncRecordUpsertRequest = {
    taskId?: string
    platform?: string
    platformName?: string
    status?: 'SYNCING' | 'DRAFT_CREATED' | 'FAILED'
    draftLink?: string
    errorMessage?: string
  }

  type ArticleSyncRecordVO = {
    id?: number
    taskId?: string
    userId?: number
    platform?: string
    platformName?: string
    status?: 'SYNCING' | 'DRAFT_CREATED' | 'FAILED'
    draftLink?: string
    errorMessage?: string
    lastSyncTime?: string
    createTime?: string
    updateTime?: string
  }

  type ArticleVO = {
    id?: number
    taskId?: string
    userId?: number
    topic?: string
    userDescription?: string
    mainTitle?: string
    subTitle?: string
    titleOptions?: TitleOption[]
    outline?: OutlineItem[]
    content?: string
    fullContent?: string
    coverImage?: string
    images?: ImageItem[]
    status?: string
    phase?: string
    errorMessage?: string
    createTime?: string
    completedTime?: string
  }

  type BaseResponseAgentExecutionStats = {
    code?: number
    data?: AgentExecutionStats
    message?: string
  }

  type BaseResponseArticleVO = {
    code?: number
    data?: ArticleVO
    message?: string
  }

  type BaseResponseBoolean = {
    code?: number
    data?: boolean
    message?: string
  }

  type BaseResponseListArticleSyncRecordVO = {
    code?: number
    data?: ArticleSyncRecordVO[]
    message?: string
  }

  type BaseResponseListOutlineSection = {
    code?: number
    data?: OutlineSection[]
    message?: string
  }

  type BaseResponseListPaymentRecord = {
    code?: number
    data?: PaymentRecord[]
    message?: string
  }

  type BaseResponseLoginUserVO = {
    code?: number
    data?: LoginUserVO
    message?: string
  }

  type BaseResponseLong = {
    code?: number
    data?: number
    message?: string
  }

  type BaseResponsePageArticleVO = {
    code?: number
    data?: PageArticleVO
    message?: string
  }

  type BaseResponsePageUserVO = {
    code?: number
    data?: PageUserVO
    message?: string
  }

  type BaseResponseStatisticsVO = {
    code?: number
    data?: StatisticsVO
    message?: string
  }

  type BaseResponseString = {
    code?: number
    data?: string
    message?: string
  }

  type BaseResponseUser = {
    code?: number
    data?: User
    message?: string
  }

  type BaseResponseUserVO = {
    code?: number
    data?: UserVO
    message?: string
  }

  type BaseResponseVoid = {
    code?: number
    data?: Record<string, any>
    message?: string
  }

  type DeleteRequest = {
    id?: number
  }

  type getArticleParams = {
    taskId: string
  }

  type getExecutionLogsParams = {
    taskId: string
  }

  type getProgressParams = {
    taskId: string
  }

  type getUserByIdParams = {
    id: number
  }

  type getUserVOByIdParams = {
    id: number
  }

  type ImageItem = {
    position?: number
    url?: string
    method?: string
    keywords?: string
    sectionTitle?: string
    description?: string
  }

  type LoginUserVO = {
    id?: number
    userAccount?: string
    userName?: string
    userAvatar?: string
    userProfile?: string
    userRole?: string
    quota?: number
    vipTime?: string
    createTime?: string
    updateTime?: string
  }

  type OutlineItem = {
    section?: number
    title?: string
    points?: string[]
  }

  type OutlineSection = {
    section?: number
    title?: string
    points?: string[]
  }

  type PageArticleVO = {
    records?: ArticleVO[]
    pageNumber?: number
    pageSize?: number
    totalPage?: number
    totalRow?: number
    optimizeCountQuery?: boolean
  }

  type PageUserVO = {
    records?: UserVO[]
    pageNumber?: number
    pageSize?: number
    totalPage?: number
    totalRow?: number
    optimizeCountQuery?: boolean
  }

  type PaymentRecord = {
    id?: number
    userId?: number
    stripeSessionId?: string
    stripePaymentIntentId?: string
    amount?: number
    currency?: string
    status?: string
    productType?: string
    description?: string
    refundTime?: string
    refundReason?: string
    createTime?: string
    updateTime?: string
  }

  type refundParams = {
    reason?: string
  }

  type SseEmitter = {
    timeout?: number
  }

  type StatisticsVO = {
    todayCount?: number
    weekCount?: number
    monthCount?: number
    totalCount?: number
    successRate?: number
    avgDurationMs?: number
    activeUserCount?: number
    totalUserCount?: number
    vipUserCount?: number
    quotaUsed?: number
  }

  type TitleOption = {
    mainTitle?: string
    subTitle?: string
  }

  type User = {
    id?: number
    userAccount?: string
    userPassword?: string
    userName?: string
    userAvatar?: string
    userProfile?: string
    userRole?: string
    quota?: number
    vipTime?: string
    editTime?: string
    createTime?: string
    updateTime?: string
    isDelete?: number
  }

  type UserAddRequest = {
    userName?: string
    userAccount?: string
    userAvatar?: string
    userProfile?: string
    userRole?: string
  }

  type UserLoginRequest = {
    userAccount?: string
    userPassword?: string
  }

  type UserQueryRequest = {
    pageNum?: number
    pageSize?: number
    sortField?: string
    sortOrder?: string
    id?: number
    userName?: string
    userAccount?: string
    userProfile?: string
    userRole?: string
  }

  type UserRegisterRequest = {
    userAccount?: string
    userPassword?: string
    checkPassword?: string
  }

  type UserUpdateRequest = {
    id?: number
    userName?: string
    userAvatar?: string
    userProfile?: string
    userRole?: string
  }

  type UserVO = {
    id?: number
    userAccount?: string
    userName?: string
    userAvatar?: string
    userProfile?: string
    userRole?: string
    createTime?: string
  }

  // ─── 热点持续监控类型 ─────────────────────────────────
  type HotspotImportance = 'low' | 'medium' | 'high' | 'urgent'

  type KeywordVO = {
    id: number
    text: string
    category?: string
    isActive: boolean
    hotspotCount: number
    createTime?: string
  }

  type RecordVO = {
    id: number
    keywordId?: number
    keywordText?: string
    title: string
    content?: string
    url: string
    source: HotspotSource
    isReal: boolean
    relevance: number
    relevanceReason?: string
    keywordMentioned: boolean
    importance: HotspotImportance
    summary?: string
    heatScore: number
    viewCount?: number
    likeCount?: number
    retweetCount?: number
    commentCount?: number
    authorName?: string
    publishedAt?: string
    createTime: string
  }

  type RecordListResponse = {
    records: RecordVO[]
    total: number
    page: number
    limit: number
    hasMore: boolean
  }

  type RecordStatsVO = {
    total: number
    today: number
    urgent: number
    activeKeywords: number
  }

  type NotificationVO = {
    id: number
    type: string
    title: string
    content?: string
    isRead: boolean
    hotspotRecordId?: number
    createTime: string
  }

  type NotificationListResponse = {
    notifications: NotificationVO[]
    unreadCount: number
  }
}
