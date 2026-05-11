<template>
  <div class="knowledge-page">
    <div class="knowledge-header">
      <h1>知识库</h1>
      <div class="upload-row">
        <input ref="fileInputRef" type="file" accept=".pdf,.md,.txt" @change="handleFileChange" />
        <a-button type="primary" :loading="uploading" @click="doUpload">上传资料</a-button>
      </div>
    </div>

    <div class="knowledge-grid">
      <!-- Document list -->
      <div class="panel">
        <div class="panel-title">文档列表</div>
        <a-spin :spinning="loadingDocs">
          <a-list :data-source="documents" bordered>
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta
                  :title="item.title"
                  :description="`${item.sourceType} · ${item.status} · ${item.chunkCount ?? 0} chunks`"
                />
                <template #extra>
                  <a-space>
                    <a-button
                      v-if="item.status === 'ready'"
                      size="small"
                      @click="openChunks(item)"
                    >
                      查看 Chunks
                    </a-button>
                    <a-popconfirm
                      title="删除后无法恢复，确定吗？"
                      ok-text="删除"
                      cancel-text="取消"
                      @confirm="doDelete(item)"
                    >
                      <a-button size="small" danger>删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-spin>
      </div>

      <!-- RAG query test -->
      <div class="panel">
        <div class="panel-title">检索测试</div>
        <a-textarea v-model:value="queryText" :rows="4" placeholder="输入检索问题" />
        <a-button class="query-btn" :loading="querying" @click="doQuery">查询</a-button>
        <pre v-if="queryResult" class="query-result">{{ queryResult }}</pre>
      </div>
    </div>

    <!-- Chunk viewer drawer -->
    <a-drawer
      v-model:open="chunkDrawerOpen"
      :title="`Chunks — ${selectedDoc?.title}`"
      width="600"
      placement="right"
    >
      <a-spin :spinning="loadingChunks">
        <div v-if="chunks.length === 0 && !loadingChunks" class="empty-hint">暂无 Chunks</div>
        <div v-for="(chunk, idx) in chunks" :key="idx" class="chunk-card">
          <div class="chunk-header">
            <span class="chunk-index">#{{ idx + 1 }}</span>
            <span class="chunk-char-count">{{ chunk.charCount }} 字符</span>
            <span v-if="chunk.title" class="chunk-title-badge">{{ chunk.title }}</span>
          </div>
          <pre class="chunk-text">{{ chunk.text }}</pre>
        </div>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  listKnowledgeDocuments,
  queryKnowledge,
  uploadKnowledge,
  deleteKnowledgeDocument,
  getDocumentChunks,
} from '@/api/knowledgeController'

const documents = ref<API.KnowledgeDocumentVO[]>([])
const loadingDocs = ref(false)
const uploading = ref(false)
const querying = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const queryText = ref('')
const queryResult = ref('')

const chunkDrawerOpen = ref(false)
const selectedDoc = ref<API.KnowledgeDocumentVO | null>(null)
const chunks = ref<any[]>([])
const loadingChunks = ref(false)

const loadDocuments = async () => {
  loadingDocs.value = true
  try {
    const res = await listKnowledgeDocuments()
    documents.value = res.data?.data ?? []
  } finally {
    loadingDocs.value = false
  }
}

const handleFileChange = () => {
  selectedFile.value = fileInputRef.value?.files?.[0] ?? null
}

const doUpload = async () => {
  if (!selectedFile.value) { message.warning('请选择文件'); return }
  uploading.value = true
  try {
    const res = await uploadKnowledge(selectedFile.value)
    if (res.data?.code === 0) {
      message.success('上传完成')
      selectedFile.value = null
      if (fileInputRef.value) fileInputRef.value.value = ''
      await loadDocuments()
    } else {
      message.error(res.data?.message || '上传失败')
    }
  } finally {
    uploading.value = false
  }
}

const doDelete = async (doc: API.KnowledgeDocumentVO) => {
  if (!doc.id) return
  const res = await deleteKnowledgeDocument(doc.id)
  if (res.data?.code === 0) {
    message.success('已删除')
    documents.value = documents.value.filter(d => d.id !== doc.id)
  } else {
    message.error(res.data?.message || '删除失败')
  }
}

const openChunks = async (doc: API.KnowledgeDocumentVO) => {
  selectedDoc.value = doc
  chunkDrawerOpen.value = true
  loadingChunks.value = true
  chunks.value = []
  try {
    const res = await getDocumentChunks(doc.id!)
    chunks.value = res.data?.data ?? []
  } finally {
    loadingChunks.value = false
  }
}

const doQuery = async () => {
  if (!queryText.value.trim()) return
  querying.value = true
  try {
    const res = await queryKnowledge({ query: queryText.value, topK: 5 })
    queryResult.value = res.data?.data ?? ''
  } finally {
    querying.value = false
  }
}

onMounted(loadDocuments)
</script>

<style scoped lang="scss">
.knowledge-page {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: var(--color-background-secondary);
}

.knowledge-header {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.knowledge-header h1 {
  margin: 0;
  font-size: 22px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 16px;
}

.panel {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.panel-title {
  font-weight: 700;
  margin-bottom: 12px;
}

.query-btn { margin-top: 12px; }

.query-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  background: #f7f8fa;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

.empty-hint {
  color: var(--color-text-secondary);
  text-align: center;
  padding: 24px 0;
}

.chunk-card {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.chunk-index {
  font-weight: 700;
  color: var(--color-primary);
}

.chunk-char-count {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.chunk-title-badge {
  font-size: 12px;
  background: #e6f4ff;
  color: #1677ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.chunk-text {
  font-size: 12px;
  background: #f7f8fa;
  padding: 10px;
  border-radius: 4px;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}

@media (max-width: 900px) {
  .knowledge-header, .upload-row {
    flex-direction: column;
    align-items: stretch;
  }
  .knowledge-grid { grid-template-columns: 1fr; }
}
</style>
