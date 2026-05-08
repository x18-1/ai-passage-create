<template>
  <div class="monitor-tab">

    <!-- 统计卡片：总热点 / 今日新增 / 紧急热点 / 监控词 -->
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
        <span>监控词</span>
        <strong>{{ stats.activeKeywords }}</strong>
      </div>
    </section>

    <!-- 排序条 -->
    <section class="sort-bar">
      <a-segmented
        v-model:value="filters.sortBy"
        :options="sortOptions"
        @change="onFilterChange"
      />
      <div class="sort-right">
        <a-button type="primary" :loading="triggering" @click="doTrigger">
          立即扫描
        </a-button>
      </div>
    </section>

    <!-- 筛选条 -->
    <section class="filter-bar">
      <a-select
        v-model:value="filters.source"
        allow-clear
        placeholder="来源"
        class="filter-item"
        @change="onFilterChange"
      >
        <a-select-option v-for="s in sourceOptions" :key="s.value" :value="s.value">{{ s.label }}</a-select-option>
      </a-select>

      <a-select
        v-model:value="filters.importance"
        allow-clear
        placeholder="重要程度"
        class="filter-item"
        @change="onFilterChange"
      >
        <a-select-option value="urgent">紧急</a-select-option>
        <a-select-option value="high">重要</a-select-option>
        <a-select-option value="medium">中等</a-select-option>
        <a-select-option value="low">一般</a-select-option>
      </a-select>

      <a-select
        v-model:value="filters.keywordId"
        allow-clear
        placeholder="关键词"
        class="filter-item"
        @change="onFilterChange"
      >
        <a-select-option v-for="kw in keywords" :key="kw.id" :value="kw.id">{{ kw.text }}</a-select-option>
      </a-select>

      <a-select
        v-model:value="filters.timeRange"
        allow-clear
        placeholder="时间范围"
        class="filter-item"
        @change="onFilterChange"
      >
        <a-select-option value="1h">1小时内</a-select-option>
        <a-select-option value="today">今天</a-select-option>
        <a-select-option value="7d">7天内</a-select-option>
        <a-select-option value="30d">30天内</a-select-option>
      </a-select>

      <a-select
        v-model:value="filters.isReal"
        allow-clear
        placeholder="真实性"
        class="filter-item"
        @change="onFilterChange"
      >
        <a-select-option :value="true">真实</a-select-option>
        <a-select-option :value="false">存疑</a-select-option>
      </a-select>

      <a-button class="reset-btn" @click="resetFilters">重置筛选</a-button>
    </section>

    <!-- 热点列表 -->
    <div v-if="loading && records.length === 0" class="list-placeholder">
      <a-spin />
    </div>

    <div v-else-if="records.length === 0" class="list-placeholder">
      <a-empty description="暂无热点记录，请先添加关键词并点击「立即扫描」" />
    </div>

    <div v-else class="record-list">
      <article v-for="item in records" :key="item.id" class="record-card">
        <div class="record-tags">
          <a-tag :color="importanceColor(item.importance)">{{ importanceLabel(item.importance) }}</a-tag>
          <a-tag :color="sourceColor(item.source)">{{ sourceLabel(item.source) }}</a-tag>
          <a-tag v-if="item.keywordText" color="purple">{{ item.keywordText }}</a-tag>
          <a-tag v-if="item.keywordMentioned" color="blue">直接提及</a-tag>
          <a-tag :color="item.isReal ? 'green' : 'orange'">{{ item.isReal ? '真实' : '存疑' }}</a-tag>
          <a-tag color="red">热 {{ Math.round(item.heatScore) }}</a-tag>
        </div>

        <h3>
          <a :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
        </h3>

        <p class="record-summary">
          <span>AI 摘要</span>{{ item.summary || item.content }}
        </p>

        <div class="record-meta">
          <span>相关性 {{ item.relevance }}%</span>
          <span v-if="item.likeCount">👍 {{ fmt(item.likeCount) }}</span>
          <span v-if="item.retweetCount">🔁 {{ fmt(item.retweetCount) }}</span>
          <span v-if="item.commentCount">💬 {{ fmt(item.commentCount) }}</span>
          <span v-if="item.viewCount">👁 {{ fmt(item.viewCount) }}</span>
          <span class="time-right">发现 {{ formatDate(item.createTime) }}</span>
          <span v-if="item.publishedAt" class="time-right">发布 {{ formatDate(item.publishedAt) }}</span>
        </div>

        <a-collapse ghost class="reason-collapse">
          <a-collapse-panel key="r" header="AI 分析理由">
            {{ item.relevanceReason || '暂无' }}
          </a-collapse-panel>
          <a-collapse-panel v-if="item.content" key="c" header="原始内容">
            {{ item.content }}
          </a-collapse-panel>
        </a-collapse>
      </article>
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination">
      <a-pagination
        v-model:current="page"
        :total="total"
        :page-size="limit"
        show-quick-jumper
        @change="loadRecords"
      />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { listKeywords, getRecordStats, listRecords, triggerMonitor } from '@/api/hotspotMonitorController'
import { useHotspotWs } from '@/composables/useHotspotWs'

const sourceOptions = [
  { label: '微博', value: 'weibo' },
  { label: 'B站', value: 'bilibili' },
  { label: '搜狗', value: 'sogou' },
  { label: 'Bing', value: 'bing' },
  { label: 'HN', value: 'hackernews' },
  { label: 'Twitter/X', value: 'twitter' },
  { label: 'DuckDuckGo', value: 'duckduckgo' },
]

const sortOptions = [
  { label: '最近发现', value: 'created_at' },
  { label: '最新发布', value: 'published_at' },
  { label: '重要程度', value: 'importance' },
  { label: '相关性', value: 'relevance' },
  { label: '热度综合', value: 'heat' },
]

const stats = ref<API.RecordStatsVO>({ total: 0, today: 0, urgent: 0, activeKeywords: 0 })
const records = ref<API.RecordVO[]>([])
const keywords = ref<API.KeywordVO[]>([])
const loading = ref(false)
const triggering = ref(false)
const page = ref(1)
const limit = ref(20)
const total = ref(0)

const filters = reactive({
  source: undefined as string | undefined,
  importance: undefined as string | undefined,
  keywordId: undefined as number | undefined,
  timeRange: undefined as string | undefined,
  isReal: undefined as boolean | undefined,
  sortBy: 'created_at',
})

function resetFilters() {
  filters.source = undefined
  filters.importance = undefined
  filters.keywordId = undefined
  filters.timeRange = undefined
  filters.isReal = undefined
  filters.sortBy = 'created_at'
  page.value = 1
  loadRecords()
}

async function loadStats() {
  try {
    const res = await getRecordStats()
    if (res.data?.data) stats.value = res.data.data
  } catch {}
}

async function loadKeywords() {
  try {
    const res = await listKeywords()
    keywords.value = res.data?.data || []
  } catch {}
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await listRecords({
      page: page.value,
      limit: limit.value,
      source: filters.source,
      importance: filters.importance,
      keywordId: filters.keywordId,
      isReal: filters.isReal,
      timeRange: filters.timeRange,
      sortBy: filters.sortBy,
      sortOrder: 'desc',
    })
    const data = res.data?.data
    if (data) {
      records.value = data.records
      total.value = data.total
    }
  } catch {
    message.error('加载热点失败')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  loadRecords()
}

async function doTrigger() {
  triggering.value = true
  try {
    await triggerMonitor()
    message.success('扫描任务已触发，稍后自动刷新')
    setTimeout(() => { loadRecords(); loadStats() }, 3000)
  } catch {
    message.error('触发失败')
  } finally {
    triggering.value = false
  }
}

useHotspotWs(() => {
  loadStats()
  if (page.value === 1) loadRecords()
})

const importanceLabel = (v: string) => ({ urgent: '紧急', high: '重要', medium: '中等', low: '一般' }[v] || v)
const importanceColor = (v: string) => ({ urgent: 'red', high: 'volcano', medium: 'gold', low: 'blue' }[v] || 'default')
const sourceLabel = (v: string) => sourceOptions.find((s) => s.value === v)?.label || v
const sourceColor = (v: string): string =>
  ({ weibo: 'red', bilibili: 'pink', sogou: 'blue', bing: 'cyan', hackernews: 'orange', twitter: 'purple', duckduckgo: 'geekblue' } as Record<string, string>)[v] || 'default'
const formatDate = (d: string) => dayjs(d).format('MM-DD HH:mm')
const fmt = (n: number) => n >= 10000 ? `${(n / 10000).toFixed(1)}万` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

onMounted(() => { loadStats(); loadKeywords(); loadRecords() })
</script>

<style scoped lang="scss">
.monitor-tab {
  padding: 8px 0;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 22px;
  box-shadow: var(--shadow-sm);
}

.stat-card span {
  color: var(--color-text-muted);
  font-size: 14px;
}

.stat-card strong {
  display: block;
  font-size: 34px;
  line-height: 1.2;
  margin-top: 12px;
  color: var(--color-text);
}

.stat-card.accent strong { color: #06b6d4; }
.stat-card.danger strong { color: #f43f5e; }
.stat-card.success strong { color: #10b981; }

/* 排序条 */
.sort-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  margin-bottom: 10px;
  box-shadow: var(--shadow-sm);
  gap: 12px;
}

.sort-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 筛选条 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 10px 16px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-sm);
}

.filter-item {
  width: 130px;
}

.reset-btn {
  margin-left: auto;
}

/* 列表 */
.list-placeholder {
  display: flex;
  justify-content: center;
  padding: 64px 0;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.record-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.record-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.record-card h3 {
  margin: 0 0 12px;
  font-size: 17px;
  line-height: 1.5;
}

.record-card h3 a {
  color: var(--color-text);
  text-decoration: none;
}

.record-card h3 a:hover {
  color: var(--color-primary);
}

.record-summary {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.7;
  margin: 0 0 12px;
}

.record-summary span {
  color: var(--color-primary);
  font-weight: 700;
  margin-right: 8px;
}

.record-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.time-right { margin-left: auto; }

.reason-collapse { margin-top: 8px; }

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding-bottom: 16px;
}

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .sort-bar { flex-direction: column; align-items: flex-start; }
  .filter-item { width: 100%; }
}
</style>
