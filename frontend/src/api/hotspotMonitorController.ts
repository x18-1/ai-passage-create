import request from '@/request'

// ─── 关键词 ───────────────────────────────────────────────
export function listKeywords() {
  return request.get<{ code: number; data: API.KeywordVO[]; message: string }>('/hotspot/keywords')
}

export function createKeyword(params: { text: string; category?: string }) {
  return request.post<{ code: number; data: number; message: string }>('/hotspot/keywords', params)
}

export function toggleKeyword(id: number) {
  return request.patch<{ code: number; data: boolean; message: string }>(`/hotspot/keywords/${id}/toggle`)
}

export function deleteKeyword(id: number) {
  return request.delete<{ code: number; data: boolean; message: string }>(`/hotspot/keywords/${id}`)
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
  return request.get<{ code: number; data: API.RecordListResponse; message: string }>('/hotspot/records', { params })
}

export function getRecordStats() {
  return request.get<{ code: number; data: API.RecordStatsVO; message: string }>('/hotspot/records/stats')
}

// ─── 通知 ─────────────────────────────────────────────────
export function listNotifications(params?: { limit?: number; unreadOnly?: boolean }) {
  return request.get<{ code: number; data: API.NotificationListResponse; message: string }>('/hotspot/notifications', { params })
}

export function markAllNotificationsRead() {
  return request.patch<{ code: number; data: boolean; message: string }>('/hotspot/notifications/read-all')
}

// ─── 监控控制 ─────────────────────────────────────────────
export function triggerMonitor() {
  return request.post<{ code: number; data: boolean; message: string }>('/hotspot/monitor/trigger')
}
