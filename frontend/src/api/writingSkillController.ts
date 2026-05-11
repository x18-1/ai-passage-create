// @ts-ignore
/* eslint-disable */
import request from '@/request'

export async function listWritingSkills(options?: { [key: string]: any }) {
  return request<API.BaseResponseListWritingSkillVO>('/writing-skills', {
    method: 'GET',
    ...(options || {}),
  })
}
