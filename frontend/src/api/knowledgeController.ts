// @ts-ignore
/* eslint-disable */
import request from '@/request'

export async function listKnowledgeDocuments(options?: { [key: string]: any }) {
  return request<API.BaseResponseListKnowledgeDocumentVO>('/knowledge/documents', {
    method: 'GET',
    ...(options || {}),
  })
}

export async function uploadKnowledge(file: File, options?: { [key: string]: any }) {
  const data = new FormData()
  data.append('file', file)
  return request<API.BaseResponseLong>('/knowledge/upload', {
    method: 'POST',
    data,
    ...(options || {}),
  })
}

export async function queryKnowledge(body: API.KnowledgeQueryRequest, options?: { [key: string]: any }) {
  return request<API.BaseResponseString>('/knowledge/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    data: body,
    ...(options || {}),
  })
}

export async function ingestArticle(taskId: string, options?: { [key: string]: any }) {
  return request<API.BaseResponseLong>(`/knowledge/articles/${taskId}/ingest`, {
    method: 'POST',
    ...(options || {}),
  })
}

export async function ingestHotspots(recordIds: number[], options?: { [key: string]: any }) {
  return request<API.BaseResponseLong>('/knowledge/hotspots/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    data: { recordIds },
    ...(options || {}),
  })
}

export async function deleteKnowledgeDocument(docId: number, options?: { [key: string]: any }) {
  return request<API.BaseResponseBoolean>(`/knowledge/documents/${docId}`, {
    method: 'DELETE',
    ...(options || {}),
  })
}

export async function getDocumentChunks(docId: number, options?: { [key: string]: any }) {
  return request<any>(`/knowledge/documents/${docId}/chunks`, {
    method: 'GET',
    ...(options || {}),
  })
}
