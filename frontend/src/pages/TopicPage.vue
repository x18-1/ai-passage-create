<template>
  <div class="topic-page">
    <section class="topic-hero">
      <div>
        <h1>热点选题</h1>
        <p>先扫描热点雷达，勾选值得写的热点，再生成可复制到创作页的选题。</p>
      </div>
      <a-space>
        <a-button size="large" :loading="radarLoading" :disabled="!keyword.trim()" @click="scanRadar">
          <template #icon>
            <RadarChartOutlined />
          </template>
          扫描热点
        </a-button>
        <a-button
          type="primary"
          size="large"
          :loading="suggestionLoading"
          :disabled="selectedHotspotUrls.length === 0"
          @click="activeTab = 'suggestions'; generateTopics()"
        >
          <template #icon>
            <ThunderboltOutlined />
          </template>
          基于已选生成
        </a-button>
      </a-space>
    </section>

    <section class="query-panel">
      <a-form layout="vertical">
        <a-form-item label="关键词">
          <a-input-search
            v-model:value="keyword"
            size="large"
            placeholder="输入热点方向，如 AI 编程、Claude Code、小红书副业"
            enter-button="扫描热点"
            :loading="radarLoading"
            @search="scanRadar"
          />
        </a-form-item>

        <div class="query-options">
          <a-form-item label="数据源">
            <a-checkbox-group v-model:value="selectedSources">
              <a-checkbox v-for="source in sourceOptions" :key="source.value" :value="source.value">
                {{ source.label }}
              </a-checkbox>
            </a-checkbox-group>
          </a-form-item>

          <a-form-item label="选题数量">
            <a-input-number v-model:value="limit" :min="1" :max="10" />
          </a-form-item>
        </div>
      </a-form>
    </section>

    <a-tabs v-model:activeKey="activeTab" class="topic-tabs">
      <a-tab-pane key="radar" tab="热点雷达">
        <section class="stats-grid">
          <div class="stat-card">
            <span>总热点</span>
            <strong>{{ stats.total }}</strong>
          </div>
          <div class="stat-card accent">
            <span>今日新增</span>
            <strong>{{ stats.today }}</strong>
          </div>
          <div class="stat-card danger">
            <span>紧急热点</span>
            <strong>{{ stats.urgent }}</strong>
          </div>
          <div class="stat-card success">
            <span>高相关</span>
            <strong>{{ stats.highRelevance }}</strong>
          </div>
        </section>

        <section class="radar-toolbar">
          <a-segmented v-model:value="sortBy" :options="sortOptions" />
          <a-select v-model:value="sourceFilter" allow-clear placeholder="来源" class="filter-select">
            <a-select-option v-for="source in sourceOptions" :key="source.value" :value="source.value">
              {{ source.label }}
            </a-select-option>
          </a-select>
          <a-select v-model:value="importanceFilter" allow-clear placeholder="重要程度" class="filter-select">
            <a-select-option value="urgent">紧急</a-select-option>
            <a-select-option value="high">重要</a-select-option>
            <a-select-option value="medium">中等</a-select-option>
            <a-select-option value="low">一般</a-select-option>
          </a-select>
          <a-button @click="resetFilters">重置</a-button>
          <span class="selected-count">已选 {{ selectedHotspotUrls.length }} 条</span>
        </section>

        <a-alert
          v-if="radarResult?.failedSources?.length"
          type="warning"
          show-icon
          class="source-alert"
          :message="`部分来源抓取失败：${radarResult.failedSources.join('、')}`"
          :description="failureDescription"
        />

        <div v-if="filteredHotspots.length" class="hotspot-list">
          <article
            v-for="item in filteredHotspots"
            :key="item.url"
            :class="['hotspot-card', { selected: selectedHotspotUrls.includes(item.url) }]"
          >
            <div class="hotspot-check">
              <a-checkbox :checked="selectedHotspotUrls.includes(item.url)" @change="toggleHotspot(item)" />
            </div>
            <div class="hotspot-body">
              <div class="hotspot-tags">
                <a-tag :color="importanceColor(item.importance)">{{ importanceText(item.importance) }}</a-tag>
                <a-tag :color="sourceColor(item.source)">{{ sourceLabel(item.source) }}</a-tag>
                <a-tag v-if="item.keywordMentioned" color="purple">直接提及</a-tag>
                <a-tag color="green">可信</a-tag>
                <a-tag color="red">热 {{ Math.round(item.heatScore) }}</a-tag>
              </div>

              <h3>
                <a :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
              </h3>

              <p class="summary">
                <span>AI 摘要</span>
                {{ item.summary || item.content }}
              </p>

              <div class="author-line">
                <UserOutlined />
                <span>{{ item.authorName || '未知作者' }}</span>
                <span>相关性 {{ item.relevance }}%</span>
                <span v-if="item.likeCount">点赞 {{ formatNumber(item.likeCount) }}</span>
                <span v-if="item.retweetCount">转发 {{ formatNumber(item.retweetCount) }}</span>
                <span v-if="item.commentCount">评论 {{ formatNumber(item.commentCount) }}</span>
                <span v-if="item.viewCount">浏览 {{ formatNumber(item.viewCount) }}</span>
              </div>

              <div class="time-line">
                <ClockCircleOutlined />
                <span v-if="item.publishedAt">发布 {{ formatDate(item.publishedAt) }}</span>
                <span>抓取刚刚</span>
              </div>

              <a-collapse ghost class="detail-collapse">
                <a-collapse-panel key="reason" header="AI 分析理由">
                  {{ item.relevanceReason || '暂无分析理由' }}
                </a-collapse-panel>
                <a-collapse-panel key="content" header="原始内容">
                  {{ item.content || item.title }}
                </a-collapse-panel>
              </a-collapse>
            </div>
          </article>
        </div>

        <a-empty v-else :description="radarLoading ? '正在扫描热点...' : '输入关键词后扫描热点雷达'" />
      </a-tab-pane>

      <a-tab-pane key="suggestions" tab="生成选题">
        <section class="suggestion-panel">
          <div class="section-header">
            <div>
              <h2>
                <BulbOutlined />
                选题建议
              </h2>
              <p>基于已选 {{ selectedHotspotUrls.length }} 条热点生成，不会重新扫描全网。</p>
            </div>
            <a-button
              type="primary"
              :loading="suggestionLoading"
              :disabled="selectedHotspotUrls.length === 0"
              @click="generateTopics"
            >
              生成选题
            </a-button>
          </div>

          <div v-if="suggestions.length" class="suggestion-list">
            <article v-for="item in suggestions" :key="item.title" class="suggestion-card">
              <div class="suggestion-title-row">
                <h3>{{ item.title }}</h3>
                <a-space>
                  <a-button size="small" @click="copyText(item.title, '选题已复制')">复制选题</a-button>
                  <a-button size="small" type="primary" @click="copyText(item.contentDescription, '内容描述已复制')">
                    复制描述
                  </a-button>
                </a-space>
              </div>

              <p class="description">{{ item.contentDescription }}</p>

              <div class="meta-grid">
                <div>
                  <span>切入角度</span>
                  <strong>{{ item.angle }}</strong>
                </div>
                <div>
                  <span>爆点理由</span>
                  <strong>{{ item.viralReason }}</strong>
                </div>
              </div>

              <div class="tag-line">
                <a-tag v-for="platform in item.suitablePlatforms" :key="platform" color="green">
                  {{ platform }}
                </a-tag>
              </div>

              <div class="source-list">
                <span>参考热点：</span>
                <em v-for="title in item.sourceHotspotTitles" :key="title">{{ title }}</em>
              </div>
            </article>
          </div>

          <a-empty v-else :description="suggestionLoading ? '正在生成选题...' : '请先在热点雷达中勾选热点'" />
        </section>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  BulbOutlined,
  ClockCircleOutlined,
  RadarChartOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { generateHotspotTopicSuggestions, scanHotspotRadar } from '@/api/hotspotController'

// 持久化到 sessionStorage，刷新页面后恢复；关闭标签页自动清除
function useSessionRef<T>(key: string, defaultValue: T) {
  const stored = sessionStorage.getItem(key)
  const initial: T = stored !== null ? (JSON.parse(stored) as T) : defaultValue
  const state = ref<T>(initial)
  watch(
    state,
    (val) => {
      if (val === null || val === undefined) {
        sessionStorage.removeItem(key)
      } else {
        sessionStorage.setItem(key, JSON.stringify(val))
      }
    },
    { deep: true },
  )
  return state
}

const sourceOptions: Array<{ label: string; value: API.HotspotSource }> = [
  { label: '微博', value: 'weibo' },
  { label: 'B站', value: 'bilibili' },
  { label: '搜狗', value: 'sogou' },
  { label: 'Bing', value: 'bing' },
  { label: 'Hacker News', value: 'hackernews' },
  { label: 'Twitter/X', value: 'twitter' },
  { label: 'Google', value: 'google' },
  { label: 'DuckDuckGo', value: 'duckduckgo' },
]

const sortOptions = [
  { label: '最新发现', value: 'created' },
  { label: '最新发布', value: 'published' },
  { label: '重要程度', value: 'importance' },
  { label: '相关性', value: 'relevance' },
  { label: '热度综合', value: 'heat' },
]

const keyword = useSessionRef('hotspot-keyword', '')
const selectedSources = useSessionRef<API.HotspotSource[]>('hotspot-sources', sourceOptions.map((item) => item.value))
const limit = useSessionRef('hotspot-limit', 5)
const activeTab = useSessionRef('hotspot-active-tab', 'radar')
const radarResult = useSessionRef<API.HotspotRadarResponse | null>('hotspot-radar-result', null)
const suggestionResult = useSessionRef<API.HotspotTopicSuggestionResponse | null>('hotspot-suggestion-result', null)
const selectedHotspotUrls = useSessionRef<string[]>('hotspot-selected-urls', [])
const sortBy = useSessionRef('hotspot-sort-by', 'heat')

const radarLoading = ref(false)
const suggestionLoading = ref(false)
const sourceFilter = ref<API.HotspotSource | undefined>()
const importanceFilter = ref<API.HotspotVO['importance'] | undefined>()

const stats = computed(() => radarResult.value?.stats || { total: 0, today: 0, urgent: 0, highRelevance: 0, sourceCount: 0 })
const suggestions = computed(() => suggestionResult.value?.suggestions || [])
const selectedHotspots = computed(() => (radarResult.value?.hotspots || []).filter((item) => selectedHotspotUrls.value.includes(item.url)))
const failureDescription = computed(() => {
  const details = radarResult.value?.failedSourceDetails || []
  return details.map((item) => `${sourceLabel(item.source)}：${item.error}`).join('；')
})
const filteredHotspots = computed(() => {
  let items = [...(radarResult.value?.hotspots || [])]
  if (sourceFilter.value) {
    items = items.filter((item) => item.source === sourceFilter.value)
  }
  if (importanceFilter.value) {
    items = items.filter((item) => item.importance === importanceFilter.value)
  }
  const importanceOrder = { urgent: 0, high: 1, medium: 2, low: 3 }
  items.sort((a, b) => {
    if (sortBy.value === 'published') {
      return new Date(b.publishedAt || 0).getTime() - new Date(a.publishedAt || 0).getTime()
    }
    if (sortBy.value === 'importance') {
      return importanceOrder[a.importance] - importanceOrder[b.importance]
    }
    if (sortBy.value === 'relevance') {
      return b.relevance - a.relevance
    }
    if (sortBy.value === 'heat') {
      return b.heatScore - a.heatScore
    }
    return 0
  })
  return items
})

const scanRadar = async () => {
  const value = keyword.value.trim()
  if (!value) {
    message.warning('请输入关键词')
    return
  }
  if (selectedSources.value.length === 0) {
    message.warning('请至少选择一个数据源')
    return
  }

  radarLoading.value = true
  try {
    const res = await scanHotspotRadar({
      keyword: value,
      sources: selectedSources.value,
      analyzeLimit: 20,
    }, { timeout: 120000 })
    radarResult.value = res.data.data || null
    selectedHotspotUrls.value = []
    suggestionResult.value = null
    activeTab.value = 'radar'
    if (!radarResult.value?.hotspots?.length) {
      message.warning('暂未扫描到可用热点，可以换个关键词或数据源重试')
    } else {
      message.success(`扫描到 ${radarResult.value.hotspots.length} 条热点`)
    }
  } catch (error: any) {
    const errorMessage = error?.code === 'ECONNABORTED'
      ? '扫描热点超时，请减少数据源或稍后重试'
      : error?.response?.data?.message || error?.message || '扫描热点失败'
    message.error(errorMessage)
  } finally {
    radarLoading.value = false
  }
}

const generateTopics = async () => {
  const value = keyword.value.trim()
  if (!value || selectedHotspots.value.length === 0) {
    message.warning('请先勾选热点')
    return
  }

  suggestionLoading.value = true
  try {
    const res = await generateHotspotTopicSuggestions({
      keyword: value,
      hotspots: selectedHotspots.value,
      limit: limit.value,
    }, { timeout: 120000 })
    suggestionResult.value = res.data.data || null
    if (!suggestionResult.value?.suggestions?.length) {
      message.warning('暂未生成可用选题，可以调整已选热点后重试')
    } else {
      message.success(`已生成 ${suggestionResult.value.suggestions.length} 个选题`)
    }
  } catch (error: any) {
    const errorMessage = error?.code === 'ECONNABORTED'
      ? '生成选题超时，请减少已选热点后重试'
      : error?.response?.data?.message || error?.message || '生成选题失败'
    message.error(errorMessage)
  } finally {
    suggestionLoading.value = false
  }
}

const toggleHotspot = (item: API.HotspotVO) => {
  if (selectedHotspotUrls.value.includes(item.url)) {
    selectedHotspotUrls.value = selectedHotspotUrls.value.filter((url) => url !== item.url)
  } else {
    selectedHotspotUrls.value = [...selectedHotspotUrls.value, item.url]
  }
}

const resetFilters = () => {
  sortBy.value = 'heat'
  sourceFilter.value = undefined
  importanceFilter.value = undefined
}

const copyText = async (text: string, successMessage: string) => {
  await navigator.clipboard.writeText(text)
  message.success(successMessage)
}

const sourceLabel = (source: API.HotspotSource) => sourceOptions.find((option) => option.value === source)?.label || source

const sourceColor = (source: API.HotspotSource) => {
  const colors: Record<API.HotspotSource, string> = {
    weibo: 'red',
    bilibili: 'pink',
    sogou: 'blue',
    bing: 'cyan',
    hackernews: 'orange',
    twitter: 'purple',
    google: 'green',
    duckduckgo: 'geekblue',
  }
  return colors[source]
}

const importanceText = (importance: API.HotspotVO['importance']) => {
  const map = { urgent: '紧急', high: '重要', medium: '中等', low: '一般' }
  return map[importance]
}

const importanceColor = (importance: API.HotspotVO['importance']) => {
  const map = { urgent: 'red', high: 'volcano', medium: 'gold', low: 'blue' }
  return map[importance]
}

const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')
const formatNumber = (value: number) => {
  if (value >= 10000) return `${(value / 10000).toFixed(1)}万`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return String(value)
}
</script>

<style scoped lang="scss">
.topic-page {
  min-height: calc(100vh - 64px);
  background: var(--color-background-secondary);
  padding: 24px;
}

.topic-hero,
.query-panel,
.stat-card,
.radar-toolbar,
.hotspot-card,
.suggestion-panel,
.suggestion-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.topic-hero {
  max-width: 1400px;
  margin: 0 auto 18px;
  padding: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.topic-hero h1 {
  margin: 0;
  color: var(--color-text);
  font-size: 26px;
  line-height: 1.25;
}

.topic-hero p,
.section-header p {
  margin: 8px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.query-panel,
.topic-tabs,
.stats-grid,
.radar-toolbar,
.hotspot-list,
.suggestion-panel {
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

.query-panel {
  margin-bottom: 18px;
  padding: 20px 22px 6px;
}

.query-options {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.topic-tabs :deep(.ant-tabs-nav) {
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  padding: 22px;
}

.stat-card span {
  color: var(--color-text-muted);
  font-size: 14px;
}

.stat-card strong {
  display: block;
  color: var(--color-text);
  font-size: 34px;
  line-height: 1.2;
  margin-top: 12px;
}

.stat-card.accent strong {
  color: #06b6d4;
}

.stat-card.danger strong {
  color: #f43f5e;
}

.stat-card.success strong {
  color: #10b981;
}

.radar-toolbar {
  padding: 12px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-select {
  width: 150px;
}

.selected-count {
  margin-left: auto;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.source-alert {
  max-width: 1400px;
  margin: 0 auto 16px;
}

.hotspot-list,
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hotspot-card {
  padding: 20px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 12px;
}

.hotspot-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.12);
}

.hotspot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hotspot-card h3,
.suggestion-card h3 {
  margin: 0;
  color: var(--color-text);
  font-size: 18px;
  line-height: 1.5;
}

.summary {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.7;
  margin: 14px 0;
}

.summary span {
  color: var(--color-primary);
  font-weight: 700;
  margin-right: 8px;
}

.author-line,
.time-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--color-text-muted);
  font-size: 13px;
  margin-top: 8px;
}

.detail-collapse {
  margin-top: 12px;
}

.suggestion-panel {
  padding: 20px;
}

.section-header,
.suggestion-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.section-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.suggestion-card {
  padding: 16px;
}

.description {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.7;
  margin: 12px 0;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 12px 0;
}

.meta-grid div {
  background: var(--color-background-secondary);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.meta-grid span {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.meta-grid strong {
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.55;
}

.tag-line,
.source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-list {
  margin-top: 12px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.source-list em {
  color: var(--color-text-secondary);
  font-style: normal;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .topic-hero,
  .query-options,
  .suggestion-title-row {
    flex-direction: column;
  }

}

@media (max-width: 640px) {
  .topic-page {
    padding: 12px;
  }

  .stats-grid,
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
