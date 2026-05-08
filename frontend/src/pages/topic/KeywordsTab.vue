<template>
  <div class="keywords-tab">
    <div class="add-form">
      <a-input
        v-model:value="newText"
        placeholder="输入关键词，如 AI 编程、Claude Code"
        class="kw-input"
        @press-enter="doCreate"
      />
      <a-input
        v-model:value="newCategory"
        placeholder="分类（可选）"
        class="cat-input"
      />
      <a-button type="primary" :loading="creating" @click="doCreate">
        + 添加
      </a-button>
    </div>

    <div v-if="loading" class="kw-loading"><a-spin /></div>

    <div v-else-if="keywords.length === 0" class="kw-empty">
      <a-empty description="还没有监控关键词，添加一个开始监控热点吧" />
    </div>

    <div v-else class="kw-grid">
      <div
        v-for="kw in keywords"
        :key="kw.id"
        :class="['kw-card', { inactive: !kw.isActive }]"
      >
        <div class="kw-main">
          <span class="kw-text">{{ kw.text }}</span>
          <a-tag v-if="kw.category" color="blue" class="kw-category">{{ kw.category }}</a-tag>
        </div>
        <div class="kw-meta">
          <span class="kw-count">{{ kw.hotspotCount }} 条热点</span>
        </div>
        <div class="kw-actions">
          <a-switch
            :checked="kw.isActive"
            size="small"
            :loading="togglingId === kw.id"
            @change="doToggle(kw)"
          />
          <a-popconfirm title="确定删除该关键词吗？" @confirm="doDelete(kw.id)">
            <a-button type="text" danger size="small" class="del-btn">删除</a-button>
          </a-popconfirm>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { listKeywords, createKeyword, toggleKeyword, deleteKeyword } from '@/api/hotspotMonitorController'

const keywords = ref<API.KeywordVO[]>([])
const loading = ref(false)
const creating = ref(false)
const togglingId = ref<number | null>(null)
const newText = ref('')
const newCategory = ref('')

async function load() {
  loading.value = true
  try {
    const res = await listKeywords()
    keywords.value = res.data?.data || []
  } catch {
    message.error('加载关键词失败')
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  const text = newText.value.trim()
  if (!text) return message.warning('请输入关键词')
  creating.value = true
  try {
    await createKeyword({ text, category: newCategory.value.trim() || undefined })
    newText.value = ''
    newCategory.value = ''
    message.success('关键词添加成功')
    await load()
  } catch (err: any) {
    message.error(err?.response?.data?.message || '添加失败')
  } finally {
    creating.value = false
  }
}

async function doToggle(kw: API.KeywordVO) {
  togglingId.value = kw.id
  try {
    await toggleKeyword(kw.id)
    kw.isActive = !kw.isActive
  } catch {
    message.error('切换失败')
  } finally {
    togglingId.value = null
  }
}

async function doDelete(id: number) {
  try {
    await deleteKeyword(id)
    keywords.value = keywords.value.filter((k) => k.id !== id)
    message.success('删除成功')
  } catch {
    message.error('删除失败')
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.keywords-tab {
  padding: 8px 0;
}

.add-form {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-sm);
}

.kw-input {
  flex: 2;
}

.cat-input {
  flex: 1;
}

.kw-loading,
.kw-empty {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.kw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kw-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: opacity 0.2s;
  box-shadow: var(--shadow-sm);
}

.kw-card.inactive {
  opacity: 0.5;
}

.kw-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.kw-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.kw-meta {
  color: var(--color-text-muted);
  font-size: 13px;
}

.kw-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
