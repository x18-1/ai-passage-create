// @ts-ignore
/* eslint-disable */
import request from '@/request'

export async function listMemories(params?: { memoryType?: string }, options?: { [key: string]: any }) {
  return request<API.BaseResponseListMemoryVO>('/memories', {
    method: 'GET',
    params,
    ...(options || {}),
  })
}

export async function createMemory(body: API.MemoryCreateRequest, options?: { [key: string]: any }) {
  return request<API.BaseResponseLong>('/memories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    data: body,
    ...(options || {}),
  })
}

export async function toggleMemory(params: { memoryId: number }, options?: { [key: string]: any }) {
  return request<API.BaseResponseBoolean>(`/memories/${params.memoryId}/toggle`, {
    method: 'PATCH',
    ...(options || {}),
  })
}

export async function deleteMemory(params: { memoryId: number }, options?: { [key: string]: any }) {
  return request<API.BaseResponseBoolean>(`/memories/${params.memoryId}`, {
    method: 'DELETE',
    ...(options || {}),
  })
}
