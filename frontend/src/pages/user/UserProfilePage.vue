<template>
  <div class="profile-page">
    <div class="profile-container">
      <h1 class="page-title">个人设置</h1>

      <!-- 写作记忆 -->
      <section class="card">
        <div class="card-header">
          <span class="card-title">写作记忆</span>
          <a-button type="primary" size="small" @click="showAddMemory = true">+ 新增记忆</a-button>
        </div>
        <p class="card-desc">记忆会在生成文章时自动注入每个 Agent 的提示词，让 AI 记住你的写作偏好。</p>

        <a-spin :spinning="loadingMemories">
          <div v-if="memories.length === 0 && !loadingMemories" class="empty-hint">
            暂无记忆，点击「新增记忆」开始添加
          </div>
          <div class="memory-list">
            <div
              v-for="mem in memories"
              :key="mem.id"
              :class="['memory-card', { inactive: !mem.isActive }]"
            >
              <div class="memory-left">
                <a-tag :color="typeColor(mem.memoryType ?? '')">{{ typeLabel(mem.memoryType ?? '') }}</a-tag>
                <span class="memory-title">{{ mem.title }}</span>
              </div>
              <div class="memory-content">{{ mem.content }}</div>
              <div class="memory-actions">
                <span class="memory-weight">权重 {{ mem.weight }}</span>
                <a-switch
                  :checked="mem.isActive"
                  size="small"
                  @change="() => doToggle(mem)"
                />
                <a-button type="link" danger size="small" @click="doDelete(mem)">删除</a-button>
              </div>
            </div>
          </div>
        </a-spin>
      </section>

      <!-- 写作 Skills -->
      <section class="card">
        <div class="card-header">
          <span class="card-title">写作 Skills</span>
        </div>
        <p class="card-desc">内置写作模板，在创建文章时勾选后注入 Agent。</p>
        <a-spin :spinning="loadingSkills">
          <div class="skills-list">
            <div v-for="skill in skills" :key="skill.ref" class="skill-card">
              <div class="skill-header">
                <span class="skill-name">{{ skill.name }}</span>
                <div class="skill-stages">
                  <a-tag v-for="s in skill.applicableStages" :key="s" color="blue" size="small">{{ s }}</a-tag>
                </div>
              </div>
              <p class="skill-desc">{{ skill.description }}</p>
              <a-collapse ghost>
                <a-collapse-panel key="1" header="查看内容">
                  <pre class="skill-content">{{ skill.content }}</pre>
                </a-collapse-panel>
              </a-collapse>
            </div>
          </div>
        </a-spin>
      </section>
    </div>

    <!-- 新增记忆弹窗 -->
    <a-modal
      v-model:open="showAddMemory"
      title="新增写作记忆"
      :confirm-loading="adding"
      @ok="doAddMemory"
      @cancel="resetForm"
    >
      <a-form layout="vertical" style="margin-top: 12px">
        <a-form-item label="记忆类型" required>
          <a-select v-model:value="form.memoryType" placeholder="选择类型">
            <a-select-option value="style">写作风格</a-select-option>
            <a-select-option value="platform">平台偏好</a-select-option>
            <a-select-option value="topic">话题倾向</a-select-option>
            <a-select-option value="constraint">内容约束</a-select-option>
            <a-select-option value="visual">配图风格</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="标题" required>
          <a-input v-model:value="form.title" placeholder="如：科技风格、不用营销语" :maxlength="80" />
        </a-form-item>
        <a-form-item label="内容" required>
          <a-textarea
            v-model:value="form.content"
            :rows="4"
            placeholder="详细描述这条记忆，AI 会严格遵守"
            :maxlength="500"
            show-count
          />
        </a-form-item>
        <a-form-item label="权重（越高优先级越高）">
          <a-slider v-model:value="form.weight" :min="0" :max="100" :step="10" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  listMemories,
  createMemory,
  toggleMemory,
  deleteMemory,
} from '@/api/memoryController'
import { listWritingSkills } from '@/api/writingSkillController'

const memories = ref<API.MemoryVO[]>([])
const loadingMemories = ref(false)
const skills = ref<API.WritingSkillVO[]>([])
const loadingSkills = ref(false)
const showAddMemory = ref(false)
const adding = ref(false)

const form = reactive<API.MemoryCreateRequest>({
  memoryType: 'style',
  title: '',
  content: '',
  weight: 60,
})

const TYPE_META: Record<string, { label: string; color: string }> = {
  style: { label: '写作风格', color: 'purple' },
  platform: { label: '平台偏好', color: 'geekblue' },
  topic: { label: '话题倾向', color: 'cyan' },
  constraint: { label: '内容约束', color: 'orange' },
  visual: { label: '配图风格', color: 'magenta' },
}

const typeLabel = (t: string) => TYPE_META[t]?.label ?? t
const typeColor = (t: string) => TYPE_META[t]?.color ?? 'default'

async function loadMemories() {
  loadingMemories.value = true
  try {
    const res = await listMemories()
    memories.value = res.data?.data ?? []
  } finally {
    loadingMemories.value = false
  }
}

async function loadSkills() {
  loadingSkills.value = true
  try {
    const res = await listWritingSkills()
    skills.value = res.data?.data ?? []
  } finally {
    loadingSkills.value = false
  }
}

async function doAddMemory() {
  if (!form.memoryType || !form.title?.trim() || !form.content?.trim()) {
    message.warning('请填写类型、标题和内容')
    return
  }
  adding.value = true
  try {
    const res = await createMemory({
      memoryType: form.memoryType,
      title: form.title.trim(),
      content: form.content.trim(),
      weight: form.weight,
    })
    if (res.data?.code === 0) {
      message.success('记忆已添加')
      showAddMemory.value = false
      resetForm()
      await loadMemories()
    } else {
      message.error(res.data?.message || '添加失败')
    }
  } finally {
    adding.value = false
  }
}

async function doToggle(mem: API.MemoryVO) {
  if (!mem.id) return
  await toggleMemory({ memoryId: mem.id })
  mem.isActive = !mem.isActive
}

async function doDelete(mem: API.MemoryVO) {
  if (!mem.id) return
  await deleteMemory({ memoryId: mem.id })
  memories.value = memories.value.filter((m) => m.id !== mem.id)
  message.success('已删除')
}

function resetForm() {
  form.memoryType = 'style'
  form.title = ''
  form.content = ''
  form.weight = 60
}

onMounted(() => {
  loadMemories()
  loadSkills()
})
</script>

<style scoped lang="scss">
.profile-page {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: var(--color-background-secondary);
}

.profile-container {
  max-width: 860px;
  margin: 0 auto;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 20px;
}

.card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.card-desc {
  color: var(--color-text-secondary);
  font-size: 13px;
  margin-bottom: 16px;
}

.empty-hint {
  color: var(--color-text-secondary);
  text-align: center;
  padding: 24px 0;
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.memory-card {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px 14px;
  transition: opacity 0.2s;

  &.inactive {
    opacity: 0.45;
  }
}

.memory-left {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.memory-title {
  font-weight: 600;
  font-size: 14px;
}

.memory-content {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  line-height: 1.5;
}

.memory-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.memory-weight {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.skills-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-card {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px 14px;
}

.skill-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.skill-name {
  font-weight: 600;
}

.skill-stages {
  display: flex;
  gap: 4px;
}

.skill-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 4px;
}

.skill-content {
  font-size: 12px;
  background: #f7f8fa;
  padding: 10px;
  border-radius: 4px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}
</style>
