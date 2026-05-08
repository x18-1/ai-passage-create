import request from '@/request'

// ─── 关键词 ───────────────────────────────────────────────
export function listKeywords() {
  return request.get<{ data: { data: API.KeywordVO[] } }>('/hotspot/keywords')
}

export function createKeyword(params: { text: string; category?: string }) {
  return request.post<{ data: { data: number } }>('/hotspot/keywords', params)
}

export function toggleKeyword(id: number) {
  return request.patch<{ data: { data: boolean } }>(`/hotspot/keywords/${id}/toggle`)
}

export function deleteKeyword(id: number) {
  return request.delete<{ data: { data: boolean } }>(`/hotspot/keywords/${id}`)
}

// ─── 热点记录 ─────────────────────────────────────────────
export function listRecords(params: {
  page?: number
  limit?: number
  source?: string
  importance?: string
  keywordId?: number
  isReal?: boolean
  timeRange?: string
  sortBy?: string
  sortOrder?: string
}) {
  return request.get<{ data: { data: API.RecordListResponse } }>('/hotspot/records', { params })
}

export function getRecordStats() {
  return request.get<{ data: { data: API.RecordStatsVO } }>('/hotspot/records/stats')
}

// ─── 通知 ─────────────────────────────────────────────────
export function listNotifications(params?: { limit?: number; unreadOnly?: boolean }) {
  return request.get<{ data: { data: API.NotificationListResponse } }>('/hotspot/notifications', { params })
}

export function markAllNotificationsRead() {
  return request.patch<{ data: { data: boolean } }>('/hotspot/notifications/read-all')
}

// ─── 监控控制 ─────────────────────────────────────────────
export function triggerMonitor() {
  return request.post<{ data: { data: boolean } }>('/hotspot/monitor/trigger')
}
