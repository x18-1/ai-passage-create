<template>
  <div class="knowledge-page">
    <section class="knowledge-header">
      <h1>知识库</h1>
      <div class="upload-row">
        <input ref="fileInputRef" type="file" accept=".pdf,.md,.txt" @change="handleFileChange" />
        <a-button type="primary" :loading="uploading" @click="doUpload">上传资料</a-button>
      </div>
    </section>

    <section class="knowledge-grid">
      <div class="panel">
        <div class="panel-title">文档</div>
        <a-list :data-source="documents" :loading="loadingDocs" bordered>
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta :title="item.title" :description="`${item.sourceType} · ${item.status} · chunks ${item.chunkCount ?? 0}`" />
            </a-list-item>
          </template>
        </a-list>
      </div>

      <div class="panel">
        <div class="panel-title">检索测试</div>
        <a-textarea v-model:value="queryText" :rows="4" placeholder="输入检索问题" />
        <a-button class="query-btn" :loading="querying" @click="doQuery">查询</a-button>
        <pre v-if="queryResult" class="query-result">{{ queryResult }}</pre>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { listKnowledgeDocuments, queryKnowledge, uploadKnowledge } from '@/api/knowledgeController'

const documents = ref<API.KnowledgeDocumentVO[]>([])
const loadingDocs = ref(false)
const uploading = ref(false)
const querying = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const queryText = ref('')
const queryResult = ref('')

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
  if (!selectedFile.value) {
    message.warning('请选择文件')
    return
  }
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

.knowledge-header,
.panel {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.knowledge-header {
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

.panel-title {
  font-weight: 700;
  margin-bottom: 12px;
}

.query-btn {
  margin-top: 12px;
}

.query-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  background: #f7f8fa;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .knowledge-header,
  .upload-row {
    align-items: stretch;
    flex-direction: column;
  }

  .knowledge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
