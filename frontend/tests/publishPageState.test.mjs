import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildPublishSession,
  resolveInitialArticle,
  toArticleRecordRequest,
} from '../src/utils/publishPageState.ts'

test('resolveInitialArticle uses route article detail when it is not in the first list page', () => {
  const firstPageArticles = [
    { taskId: 'task-first', status: 'COMPLETED', fullContent: 'first content' },
  ]
  const routeArticle = { taskId: 'task-route', status: 'COMPLETED', fullContent: 'route content' }

  const selected = resolveInitialArticle(firstPageArticles, routeArticle, 'task-route')

  assert.equal(selected?.taskId, 'task-route')
})

test('toArticleRecordRequest keeps the publish session taskId after article selection changes', () => {
  const session = buildPublishSession('task-a')
  const platform = {
    type: 'juejin',
    title: '掘金',
    displayName: '掘金',
    publishStatus: 'success',
    draftLink: 'https://juejin.cn/editor/drafts/1',
  }

  const request = toArticleRecordRequest(platform, session)

  assert.equal(request?.taskId, 'task-a')
  assert.equal(request?.platform, 'juejin')
  assert.equal(request?.status, 'DRAFT_CREATED')
})
