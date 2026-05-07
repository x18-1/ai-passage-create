// @ts-ignore
/* eslint-disable */
import request from '@/request'

export async function listArticleSyncRecords(taskId: string, options?: { [key: string]: any }) {
  return request<API.BaseResponseListArticleSyncRecordVO>(`/article-sync/records/${taskId}`, {
    method: 'GET',
    ...(options || {}),
  })
}

export async function upsertArticleSyncRecord(
  body: API.ArticleSyncRecordUpsertRequest,
  options?: { [key: string]: any },
) {
  return request<API.BaseResponseBoolean>('/article-sync/record', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}
