import assert from 'node:assert/strict'
import test from 'node:test'

import { buildCreateArticlePayload } from '../src/utils/articleContextOptions.ts'

test('buildCreateArticlePayload serializes context options', () => {
  const payload = buildCreateArticlePayload('AI 编程', {
    style: 'tech',
    enabledImageMethods: ['PEXELS'],
    enableMemory: true,
    enableRag: true,
    enabledSkillRefs: ['system/tech-media-analysis', 'system/xiaohongshu-seeding'],
    ragCollections: ['user_1_knowledge'],
  })

  assert.equal(payload.topic, 'AI 编程')
  assert.equal(payload.style, 'tech')
  assert.deepEqual(payload.enabledImageMethods, ['PEXELS'])
  assert.equal(payload.enableMemory, true)
  assert.equal(payload.enableRag, true)
  assert.deepEqual(payload.enabledSkillRefs, ['system/tech-media-analysis', 'system/xiaohongshu-seeding'])
  assert.deepEqual(payload.ragCollections, ['user_1_knowledge'])
})
