export type PublishStatus = 'idle' | 'syncing' | 'success' | 'failed'

export interface PublishableArticle {
  taskId?: string
  status?: string
  content?: string
  fullContent?: string
}

export interface PublishPlatformState {
  type: string
  title?: string
  displayName?: string
  publishStatus: PublishStatus
  draftLink?: string
  error?: string
}

export interface PublishSession {
  taskId: string
}

export interface ArticleSyncRecordRequest {
  taskId: string
  platform: string
  platformName: string
  status: 'SYNCING' | 'DRAFT_CREATED' | 'FAILED'
  draftLink?: string
  errorMessage?: string
}

export const isPublishableArticle = <T extends PublishableArticle>(
  article?: T | null,
): article is T & { taskId: string } => {
  return Boolean(article?.taskId && article.status === 'COMPLETED' && (article.fullContent || article.content))
}

export const resolveInitialArticle = <T extends PublishableArticle>(
  articles: T[],
  routeArticle: T | undefined,
  routeTaskId: string,
): T | undefined => {
  if (routeTaskId) {
    const matchedArticle = articles.find((item) => item.taskId === routeTaskId)
    if (matchedArticle) return matchedArticle
    if (isPublishableArticle(routeArticle) && routeArticle?.taskId === routeTaskId) return routeArticle
  }
  return articles[0]
}

export const buildPublishSession = (taskId?: string | null): PublishSession | null => {
  return taskId ? { taskId } : null
}

export const toRecordStatus = (
  status: PublishStatus,
): ArticleSyncRecordRequest['status'] | undefined => {
  if (status === 'success') return 'DRAFT_CREATED'
  if (status === 'failed') return 'FAILED'
  if (status === 'syncing') return 'SYNCING'
  return undefined
}

export const toArticleRecordRequest = (
  platform: PublishPlatformState,
  session: PublishSession | null,
): ArticleSyncRecordRequest | undefined => {
  const status = toRecordStatus(platform.publishStatus)
  if (!session || !status) return undefined

  return {
    taskId: session.taskId,
    platform: platform.type,
    platformName: platform.displayName || platform.title || platform.type,
    status,
    draftLink: platform.draftLink,
    errorMessage: platform.error,
  }
}
