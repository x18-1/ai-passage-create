// @ts-ignore
/* eslint-disable */
import request from '@/request'

export async function generateHotspotTopicSuggestions(
  body: API.HotspotTopicSuggestionRequest,
  options?: { [key: string]: any },
) {
  return request<API.BaseResponseHotspotTopicSuggestionResponse>('/hotspot/topic-suggestions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

export async function scanHotspotRadar(
  body: API.HotspotRadarRequest,
  options?: { [key: string]: any },
) {
  return request<API.BaseResponseHotspotRadarResponse>('/hotspot/radar', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}
