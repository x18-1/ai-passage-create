<template>
  <div class="publish-page">
    <div class="publish-shell">
      <aside class="article-sidebar">
        <div class="panel-header">
          <div>
            <h2>选择文章</h2>
            <p>仅展示已完成的文章</p>
          </div>
          <a-button :loading="articlesLoading" @click="loadArticles">
            <template #icon>
              <ReloadOutlined />
            </template>
          </a-button>
        </div>

        <a-input-search
          v-model:value="articleKeyword"
          placeholder="搜索标题或选题"
          allow-clear
          class="article-search"
        />

        <div class="article-list">
          <button
            v-for="item in filteredArticles"
            :key="item.taskId"
            :class="['article-item', { active: selectedArticle?.taskId === item.taskId }]"
            type="button"
            @click="selectArticle(item)"
          >
            <span class="article-title">{{ item.mainTitle || item.topic || '未命名文章' }}</span>
            <span class="article-topic">{{ item.subTitle || item.topic || '无摘要' }}</span>
            <span class="article-time">{{ item.createTime ? formatDate(item.createTime) : '' }}</span>
          </button>

          <a-empty v-if="!articlesLoading && filteredArticles.length === 0" description="暂无可发布文章" />
        </div>
      </aside>

      <main class="publish-main">
        <div class="main-header">
          <div>
            <h1>发布中心</h1>
            <p>将 AI 文章同步到各平台草稿箱，发布前仍可在目标平台检查和调整。</p>
          </div>
          <a-button type="primary" :disabled="!canPublish" :loading="publishing" @click="publishSelected">
            <template #icon>
              <SendOutlined />
            </template>
            同步到草稿箱
          </a-button>
        </div>

        <a-tabs v-model:activeKey="activeTab" class="publish-tabs">
          <a-tab-pane key="content" tab="内容预览">
            <div class="content-grid">
              <section class="content-panel">
                <h2>
                  <FileTextOutlined />
                  文章信息
                </h2>
                <a-form layout="vertical">
                  <a-form-item label="标题 *">
                    <a-input v-model:value="draft.title" placeholder="选择文章后自动填充" />
                  </a-form-item>
                  <a-form-item label="封面图片 URL">
                    <a-input v-model:value="draft.cover" placeholder="https://example.com/cover.jpg" />
                  </a-form-item>
                  <a-form-item label="标签">
                    <div class="tag-row">
                      <a-input
                        v-model:value="tagInput"
                        placeholder="输入标签后按回车"
                        @pressEnter.prevent="addTag"
                      />
                      <a-button @click="addTag">添加</a-button>
                    </div>
                    <div class="tag-list">
                      <a-tag v-for="tag in draft.tags" :key="tag" closable @close.prevent="removeTag(tag)">
                        {{ tag }}
                      </a-tag>
                    </div>
                  </a-form-item>
                  <a-form-item label="摘要">
                    <a-textarea v-model:value="draft.summary" :rows="5" placeholder="用于发布前自查，不会覆盖原文章" />
                  </a-form-item>
                </a-form>
              </section>

              <section class="markdown-panel">
                <h2>
                  <CodeOutlined />
                  Markdown 内容
                </h2>
                <a-textarea
                  v-model:value="draft.markdown"
                  :rows="22"
                  placeholder="选择文章后自动填充 Markdown 内容"
                  class="markdown-editor"
                />
              </section>
            </div>
          </a-tab-pane>

          <a-tab-pane key="platforms" tab="发布平台">
            <section class="platform-section">
              <div class="platform-toolbar">
                <div>
                  <h2>
                    <DeploymentUnitOutlined />
                    发布平台
                    <span>({{ selectedPlatformIds.length }}/{{ authenticatedPlatforms.length }} 已选择)</span>
                  </h2>
                  <p>{{ extensionHint }}</p>
                </div>
                <div class="toolbar-actions">
                  <a-button :loading="platformsLoading" @click="refreshPlatforms">
                    <template #icon>
                      <ReloadOutlined />
                    </template>
                    刷新
                  </a-button>
                  <a-button type="link" :disabled="authenticatedPlatforms.length === 0" @click="toggleSelectAll">
                    {{ allAuthenticatedSelected ? '取消全选' : '全选' }}
                  </a-button>
                </div>
              </div>

              <div class="platform-grid">
                <div
                  v-for="platform in platforms"
                  :key="platform.type"
                  :class="['platform-card', platform.status, platform.publishStatus, { selected: selectedPlatformIds.includes(platform.type) }]"
                >
                  <div class="platform-card-top">
                    <a-checkbox
                      :checked="selectedPlatformIds.includes(platform.type)"
                      :disabled="platform.status !== 'authenticated' || publishing"
                      @change="togglePlatform(platform.type)"
                    />
                    <div class="platform-name">{{ platform.displayName || platform.title }}</div>
                    <CheckCircleOutlined v-if="platform.status === 'authenticated'" class="status-icon ok" />
                    <ExclamationCircleOutlined v-else-if="platform.status === 'unauthenticated'" class="status-icon warn" />
                    <QuestionCircleOutlined v-else class="status-icon muted" />
                  </div>

                  <div class="platform-status">
                    <template v-if="platform.publishStatus === 'syncing'">同步中：{{ platform.message || '准备同步...' }}</template>
                    <template v-else-if="platform.publishStatus === 'success'">草稿已创建</template>
                    <template v-else-if="platform.publishStatus === 'failed'">失败：{{ platform.error || '未知错误' }}</template>
                    <template v-else-if="platform.status === 'authenticated'">已登录：{{ platform.uid || platform.title }}</template>
                    <template v-else-if="platform.status === 'unauthenticated'">未登录</template>
                    <template v-else>未查询</template>
                  </div>

                  <div class="platform-actions">
                    <a v-if="platform.draftLink" :href="platform.draftLink" target="_blank" rel="noreferrer">查看草稿</a>
                    <a v-else :href="platform.home" target="_blank" rel="noreferrer">
                      {{ platform.status === 'authenticated' ? '打开平台' : '去登录' }}
                    </a>
                  </div>
                </div>
              </div>
            </section>
          </a-tab-pane>

          <a-tab-pane key="drafts" tab="草稿状态">
            <section class="draft-section">
              <div class="draft-header">
                <div>
                  <h2>
                    <CheckCircleOutlined />
                    草稿状态
                  </h2>
                  <p>{{ selectedArticle ? (selectedArticle.mainTitle || selectedArticle.topic) : '请选择一篇文章' }}</p>
                </div>
                <a-button type="primary" :disabled="!canPublish" :loading="publishing" @click="publishSelected">
                  <template #icon>
                    <SendOutlined />
                  </template>
                  再次同步
                </a-button>
              </div>

              <div v-if="draftStatusPlatforms.length > 0" class="draft-list">
                <div
                  v-for="platform in draftStatusPlatforms"
                  :key="platform.type"
                  :class="['draft-item', platform.publishStatus]"
                >
                  <div>
                    <div class="draft-platform">{{ platform.displayName || platform.title }}</div>
                    <div class="draft-message">
                      <template v-if="platform.publishStatus === 'syncing'">{{ platform.message || '同步中...' }}</template>
                      <template v-else-if="platform.publishStatus === 'success'">草稿已创建</template>
                      <template v-else-if="platform.publishStatus === 'failed'">{{ platform.error || '同步失败' }}</template>
                    </div>
                  </div>
                  <a-button
                    v-if="platform.draftLink"
                    type="link"
                    :href="platform.draftLink"
                    target="_blank"
                  >
                    查看草稿
                  </a-button>
                </div>
              </div>

              <a-empty v-else description="当前文章还没有同步记录" />
            </section>
          </a-tab-pane>
        </a-tabs>
      </main>

      <aside class="guide-sidebar">
        <div class="guide-card">
          <h2>
            <SettingOutlined />
            操作说明
          </h2>
          <ol>
            <li>
              安装并启用
              <a href="https://www.wechatsync.com/#developer" target="_blank" rel="noreferrer">
                Wechatsync Chrome 扩展
              </a>
              。
            </li>
            <li>在浏览器里登录需要发布的平台账号。</li>
            <li>点击“刷新”查询平台登录状态。</li>
            <li>选择文章和平台后同步到草稿箱。</li>
          </ol>
        </div>

        <div class="guide-card compact">
          <h2>
            <ApiOutlined />
            扩展状态
          </h2>
          <div :class="['extension-state', extensionAvailable ? 'ok' : 'warn']">
            {{ extensionAvailable ? '已检测到扩展 API' : '未检测到扩展 API' }}
          </div>
          <a-button block @click="refreshPlatforms">
            检查扩展与登录状态
          </a-button>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  ApiOutlined,
  CheckCircleOutlined,
  CodeOutlined,
  DeploymentUnitOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  SendOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'
import { getArticle, listArticle } from '@/api/articleController'
import { listArticleSyncRecords, upsertArticleSyncRecord } from '@/api/articleSyncController'
import {
  getWechatsyncAccounts,
  isWechatsyncAvailable,
  platformFromAccount,
  publishWithWechatsync,
  type SyncerAccount,
  type SyncerPlatform,
  type SyncerTaskUpdate,
} from '@/utils/wechatsync'

const SUPPORTED_PLATFORMS: SyncerPlatform[] = [
  { type: 'weixin', title: '微信公众号', displayName: '微信公众号', home: 'https://mp.weixin.qq.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'zhihu', title: '知乎', displayName: '知乎', home: 'https://www.zhihu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'weibo', title: '微博', displayName: '微博', home: 'https://weibo.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'xiaohongshu', title: '小红书', displayName: '小红书', home: 'https://creator.xiaohongshu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'juejin', title: '掘金', displayName: '掘金', home: 'https://juejin.cn/', status: 'unknown', publishStatus: 'idle' },
  { type: 'csdn', title: 'CSDN', displayName: 'CSDN', home: 'https://mp.csdn.net/', status: 'unknown', publishStatus: 'idle' },
  { type: 'jianshu', title: '简书', displayName: '简书', home: 'https://www.jianshu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'toutiao', title: '今日头条', displayName: '今日头条', home: 'https://mp.toutiao.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'douyin', title: '抖音图文', displayName: '抖音图文', home: 'https://creator.douyin.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'bilibili', title: 'B站专栏', displayName: 'B站专栏', home: 'https://member.bilibili.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'baijiahao', title: '百家号', displayName: '百家号', home: 'https://baijiahao.baidu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'yuque', title: '语雀', displayName: '语雀', home: 'https://www.yuque.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'douban', title: '豆瓣', displayName: '豆瓣', home: 'https://www.douban.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'sohu', title: '搜狐号', displayName: '搜狐号', home: 'https://mp.sohu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'xueqiu', title: '雪球', displayName: '雪球', home: 'https://xueqiu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'woshipm', title: '人人都是产品经理', displayName: '人人都是产品经理', home: 'https://www.woshipm.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'dayu', title: '大鱼号', displayName: '大鱼号', home: 'https://mp.dayu.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'yidian', title: '一点号', displayName: '一点号', home: 'https://mp.yidianzixun.com/', status: 'unknown', publishStatus: 'idle' },
  { type: '51cto', title: '51CTO', displayName: '51CTO', home: 'https://blog.51cto.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'imooc', title: '慕课手记', displayName: '慕课手记', home: 'https://www.imooc.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'oschina', title: '开源中国', displayName: '开源中国', home: 'https://my.oschina.net/', status: 'unknown', publishStatus: 'idle' },
  { type: 'segmentfault', title: '思否', displayName: '思否', home: 'https://segmentfault.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'cnblogs', title: '博客园', displayName: '博客园', home: 'https://i.cnblogs.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'sohufocus', title: '搜狐焦点', displayName: '搜狐焦点', home: 'https://mp.focus.cn/', status: 'unknown', publishStatus: 'idle' },
  { type: 'x', title: 'Twitter/X', displayName: 'Twitter/X', home: 'https://x.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'eastmoney', title: '东方财富', displayName: '东方财富', home: 'https://mp.eastmoney.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'smzdm', title: '什么值得买', displayName: '什么值得买', home: 'https://post.smzdm.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'netease', title: '网易号', displayName: '网易号', home: 'https://mp.163.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'wordpress', title: 'WordPress', displayName: 'WordPress', home: 'https://wordpress.com/', status: 'unknown', publishStatus: 'idle' },
  { type: 'typecho', title: 'Typecho', displayName: 'Typecho', home: 'https://typecho.org/', status: 'unknown', publishStatus: 'idle' },
  { type: 'zip-download', title: 'Markdown 压缩包', displayName: 'Markdown 压缩包', home: 'https://www.wechatsync.com/#developer', status: 'unknown', publishStatus: 'idle' },
]

interface ArticleSyncSnapshot {
  platforms: SyncerPlatform[]
  selectedPlatformIds: string[]
}

const route = useRoute()
const activeTab = ref('content')
const articlesLoading = ref(false)
const platformsLoading = ref(false)
const publishing = ref(false)
const extensionAvailable = ref(false)
const articleKeyword = ref('')
const tagInput = ref('')
const articles = ref<API.ArticleVO[]>([])
const selectedArticle = ref<API.ArticleVO | null>(null)
const selectedPlatformIds = ref<string[]>([])
const platforms = ref<SyncerPlatform[]>(SUPPORTED_PLATFORMS.map((item) => ({ ...item })))
const articleSyncSnapshots = ref<Record<string, ArticleSyncSnapshot>>({})

const draft = reactive({
  title: '',
  cover: '',
  summary: '',
  tags: [] as string[],
  markdown: '',
})

const filteredArticles = computed(() => {
  const keyword = articleKeyword.value.trim().toLowerCase()
  if (!keyword) return articles.value
  return articles.value.filter((item) => {
    return (
      item.mainTitle?.toLowerCase().includes(keyword) ||
      item.topic?.toLowerCase().includes(keyword) ||
      item.subTitle?.toLowerCase().includes(keyword)
    )
  })
})

const authenticatedPlatforms = computed(() => platforms.value.filter((item) => item.status === 'authenticated'))
const draftStatusPlatforms = computed(() => platforms.value.filter((item) => item.publishStatus !== 'idle'))
const allAuthenticatedSelected = computed(() => {
  return authenticatedPlatforms.value.length > 0 && authenticatedPlatforms.value.every((item) => selectedPlatformIds.value.includes(item.type))
})
const canPublish = computed(() => {
  return Boolean(draft.title.trim() && draft.markdown.trim() && selectedPlatformIds.value.length > 0 && extensionAvailable.value)
})
const extensionHint = computed(() => {
  if (!extensionAvailable.value) return '未检测到扩展，请安装并刷新页面后重试。'
  if (authenticatedPlatforms.value.length === 0) return '尚未查询到已登录平台，请先在浏览器中登录目标平台。'
  return '选择已登录的平台后，文章会同步为草稿。'
})

const loadArticles = async () => {
  articlesLoading.value = true
  try {
    const res = await listArticle({ pageNum: 1, pageSize: 50, status: 'COMPLETED' })
    const records = res.data.data?.records || []
    articles.value = records.filter((item) => item.status === 'COMPLETED' && (item.fullContent || item.content))
    if (!selectedArticle.value && articles.value.length > 0) {
      const routeTaskId = typeof route.query.taskId === 'string' ? route.query.taskId : ''
      const initialArticle = articles.value.find((item) => item.taskId === routeTaskId) || articles.value[0]
      await selectArticle(initialArticle)
    }
  } catch (error) {
    message.error((error as Error).message || '加载文章失败')
  } finally {
    articlesLoading.value = false
  }
}

const selectArticle = async (item: API.ArticleVO) => {
  if (!item.taskId) return
  try {
    saveCurrentArticleSyncState()
    const res = await getArticle({ taskId: item.taskId })
    const detail = res.data.data || item
    selectedArticle.value = detail
    draft.title = detail.mainTitle || detail.topic || ''
    draft.cover = detail.coverImage || ''
    draft.summary = ''
    draft.tags = buildDefaultTags(detail)
    draft.markdown = detail.fullContent || detail.content || ''
    restoreArticleSyncState(item.taskId)
    await loadPersistedSyncRecords(item.taskId)
  } catch (error) {
    message.error((error as Error).message || '加载文章详情失败')
  }
}

const loadPersistedSyncRecords = async (taskId: string) => {
  try {
    const res = await listArticleSyncRecords(taskId)
    const records = res.data.data || []
    if (records.length === 0) return

    const recordMap = new Map(records.map((record) => [record.platform, record]))
    platforms.value = platforms.value.map((platform) => {
      const record = recordMap.get(platform.type)
      if (!record) return platform
      return {
        ...platform,
        displayName: record.platformName || platform.displayName,
        publishStatus: toPublishStatus(record.status),
        draftLink: record.draftLink,
        error: record.errorMessage,
        message: record.status === 'SYNCING' ? '同步中...' : undefined,
      }
    })
    selectedPlatformIds.value = records.map((record) => record.platform).filter(Boolean) as string[]
    saveCurrentArticleSyncState()
  } catch (error) {
    console.error('加载草稿同步记录失败:', error)
  }
}

const toPublishStatus = (status?: API.ArticleSyncRecordVO['status']) => {
  if (status === 'DRAFT_CREATED') return 'success' as const
  if (status === 'FAILED') return 'failed' as const
  if (status === 'SYNCING') return 'syncing' as const
  return 'idle' as const
}

const toRecordStatus = (status: SyncerPlatform['publishStatus']): API.ArticleSyncRecordUpsertRequest['status'] => {
  if (status === 'success') return 'DRAFT_CREATED'
  if (status === 'failed') return 'FAILED'
  if (status === 'syncing') return 'SYNCING'
  return undefined
}

const persistSyncRecord = (platform: SyncerPlatform) => {
  const taskId = selectedArticle.value?.taskId
  const status = toRecordStatus(platform.publishStatus)
  if (!taskId || !status) return

  upsertArticleSyncRecord({
    taskId,
    platform: platform.type,
    platformName: platform.displayName || platform.title,
    status,
    draftLink: platform.draftLink,
    errorMessage: platform.error,
  }).catch((error) => {
    console.error('保存草稿同步记录失败:', error)
  })
}

const persistSelectedSyncingRecords = () => {
  platforms.value
    .filter((platform) => selectedPlatformIds.value.includes(platform.type) && platform.publishStatus === 'syncing')
    .forEach(persistSyncRecord)
}

const clonePlatforms = (items: SyncerPlatform[]) => items.map((item) => ({ ...item }))

const resetPublishState = (platform: SyncerPlatform): SyncerPlatform => ({
  ...platform,
  publishStatus: 'idle',
  message: undefined,
  error: undefined,
  draftLink: undefined,
})

const saveCurrentArticleSyncState = () => {
  const taskId = selectedArticle.value?.taskId
  if (!taskId) return
  articleSyncSnapshots.value = {
    ...articleSyncSnapshots.value,
    [taskId]: {
      platforms: clonePlatforms(platforms.value),
      selectedPlatformIds: [...selectedPlatformIds.value],
    },
  }
}

const restoreArticleSyncState = (taskId: string) => {
  const snapshot = articleSyncSnapshots.value[taskId]
  if (snapshot) {
    platforms.value = clonePlatforms(snapshot.platforms)
    selectedPlatformIds.value = [...snapshot.selectedPlatformIds]
    return
  }
  platforms.value = platforms.value.map(resetPublishState)
  selectedPlatformIds.value = []
}

const buildDefaultTags = (article: API.ArticleVO): string[] => {
  const values = [article.topic].filter(Boolean) as string[]
  return Array.from(new Set(values)).slice(0, 5)
}

const refreshPlatforms = async () => {
  platformsLoading.value = true
  extensionAvailable.value = isWechatsyncAvailable()
  try {
    const accounts = await getWechatsyncAccounts()
    mergeAccounts(accounts)
    saveCurrentArticleSyncState()
    if (accounts.length === 0) {
      message.warning('未查询到已登录平台，请先在浏览器中登录目标平台')
    } else {
      message.success(`已查询到 ${accounts.length} 个已登录平台`)
    }
  } catch (error) {
    extensionAvailable.value = false
    platforms.value = platforms.value.map((item) => ({ ...item, status: 'unknown', publishStatus: 'idle', message: undefined, error: undefined, draftLink: undefined }))
    saveCurrentArticleSyncState()
    message.error((error as Error).message || '查询扩展状态失败')
  } finally {
    platformsLoading.value = false
  }
}

const mergeAccounts = (accounts: SyncerAccount[]) => {
  const accountMap = new Map(accounts.map((account) => [account.type, account]))
  const knownTypes = new Set(platforms.value.map((item) => item.type))
  const merged: SyncerPlatform[] = platforms.value.map((platform) => {
    const account = accountMap.get(platform.type)
    if (account) {
      return {
        ...platformFromAccount(account),
        publishStatus: platform.publishStatus,
        message: platform.message,
        error: platform.error,
        draftLink: platform.draftLink,
        home: account.home || platform.home,
      }
    }
    return {
      ...platform,
      status: 'unauthenticated' as const,
      publishStatus: platform.publishStatus === 'syncing' ? 'idle' as const : platform.publishStatus,
    }
  })

  for (const account of accounts) {
    if (!knownTypes.has(account.type)) {
      merged.push(platformFromAccount(account))
    }
  }

  platforms.value = merged
  selectedPlatformIds.value = selectedPlatformIds.value.filter((id) => accountMap.has(id))
}

const toggleSelectAll = () => {
  if (allAuthenticatedSelected.value) {
    selectedPlatformIds.value = []
    return
  }
  selectedPlatformIds.value = authenticatedPlatforms.value.map((item) => item.type)
}

const togglePlatform = (type: string) => {
  const platform = platforms.value.find((item) => item.type === type)
  if (!platform || platform.status !== 'authenticated' || publishing.value) return

  if (selectedPlatformIds.value.includes(type)) {
    selectedPlatformIds.value = selectedPlatformIds.value.filter((id) => id !== type)
  } else {
    selectedPlatformIds.value = [...selectedPlatformIds.value, type]
  }
}

const publishSelected = async () => {
  if (!canPublish.value) return
  const selectedAccounts = platforms.value.filter((item) => selectedPlatformIds.value.includes(item.type) && item.status === 'authenticated')
    publishing.value = true
  activeTab.value = 'drafts'
  platforms.value = platforms.value.map((item) => {
    if (!selectedPlatformIds.value.includes(item.type)) return item
    return { ...item, publishStatus: 'syncing', message: '准备同步...', error: undefined, draftLink: undefined }
  })
  saveCurrentArticleSyncState()
  persistSelectedSyncingRecords()

  try {
    await publishWithWechatsync(
      {
        title: draft.title.trim(),
        markdown: draft.markdown,
        cover: draft.cover || undefined,
      },
      selectedAccounts,
      applyTaskUpdate,
    )
    message.success('同步任务已提交，请查看平台状态')
  } catch (error) {
    const errorMessage = (error as Error).message || '同步失败'
    platforms.value = platforms.value.map((item) => {
      if (!selectedPlatformIds.value.includes(item.type) || item.publishStatus !== 'syncing') return item
      return { ...item, publishStatus: 'failed', error: errorMessage, message: undefined }
    })
    saveCurrentArticleSyncState()
    message.error(errorMessage)
  } finally {
    publishing.value = false
  }
}

const applyTaskUpdate = (task: SyncerTaskUpdate) => {
  if (!task.accounts) return
  const updateMap = new Map(task.accounts.map((account) => [account.type, account]))
  platforms.value = platforms.value.map((platform) => {
    const update = updateMap.get(platform.type)
    if (!update) return platform
    if (update.status === 'done') {
      const next = { ...platform, publishStatus: 'success' as const, message: undefined, error: undefined, draftLink: update.editResp?.draftLink }
      persistSyncRecord(next)
      return next
    }
    if (update.status === 'failed') {
      const next = { ...platform, publishStatus: 'failed' as const, message: undefined, error: update.error || '同步失败', draftLink: undefined }
      persistSyncRecord(next)
      return next
    }
    if (update.status === 'uploading' || update.status === 'pending') {
      const next = { ...platform, publishStatus: 'syncing' as const, message: update.msg || '同步中...', error: undefined }
      persistSyncRecord(next)
      return next
    }
    return platform
  })
  saveCurrentArticleSyncState()
}

const addTag = () => {
  const value = tagInput.value.trim()
  if (!value || draft.tags.includes(value)) return
  draft.tags.push(value)
  tagInput.value = ''
}

const removeTag = (tag: string) => {
  draft.tags = draft.tags.filter((item) => item !== tag)
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

onMounted(async () => {
  extensionAvailable.value = isWechatsyncAvailable()
  await loadArticles()
})
</script>

<style scoped lang="scss">
.publish-page {
  min-height: calc(100vh - 64px);
  background: var(--color-background-secondary);
  padding: 22px;
}

.publish-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 300px;
  gap: 18px;
  max-width: 1500px;
  margin: 0 auto;
}

.article-sidebar,
.publish-main,
.guide-sidebar {
  min-width: 0;
}

.article-sidebar,
.publish-main,
.guide-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.article-sidebar {
  height: calc(100vh - 108px);
  padding: 18px;
  position: sticky;
  top: 86px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header,
.main-header,
.platform-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.panel-header h2,
.guide-card h2,
.platform-toolbar h2,
.content-panel h2,
.markdown-panel h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 17px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-header p,
.main-header p,
.platform-toolbar p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.article-search {
  margin: 18px 0 12px;
}

.article-list {
  overflow-y: auto;
  padding-right: 4px;
}

.article-item {
  width: 100%;
  border: 1px solid var(--color-border);
  background: #fff;
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 10px;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.article-item:hover,
.article-item.active {
  border-color: var(--color-primary);
  background: rgba(34, 197, 94, 0.08);
}

.article-title,
.article-topic,
.article-time {
  display: block;
}

.article-title {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.45;
}

.article-topic {
  color: var(--color-text-secondary);
  font-size: 12px;
  margin-top: 6px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-time {
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 8px;
}

.publish-main {
  padding: 22px;
}

.main-header {
  margin-bottom: 12px;
}

.main-header h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  color: var(--color-text);
}

.publish-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 18px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.95fr) minmax(320px, 1.25fr);
  gap: 18px;
}

.content-panel,
.markdown-panel,
.platform-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px;
}

.content-panel h2,
.markdown-panel h2 {
  margin-bottom: 18px;
}

.tag-row {
  display: flex;
  gap: 8px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.markdown-editor {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  line-height: 1.7;
}

.platform-toolbar,
.draft-header {
  margin-bottom: 18px;
}

.platform-toolbar h2 span {
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.platform-card {
  min-height: 128px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  background: #fff;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.platform-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.12);
}

.platform-card.success {
  border-color: #22c55e;
}

.platform-card.failed {
  border-color: #ff4d4f;
}

.platform-card.syncing {
  border-color: #1677ff;
}

.platform-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.platform-name {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 700;
  flex: 1;
}

.status-icon {
  font-size: 18px;
}

.status-icon.ok {
  color: #22c55e;
}

.status-icon.warn {
  color: #f59e0b;
}

.status-icon.muted {
  color: var(--color-text-muted);
}

.platform-status {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.5;
  margin: 12px 0;
  word-break: break-word;
}

.platform-card.authenticated .platform-status,
.platform-card.success .platform-status {
  color: #16a34a;
  font-weight: 600;
}

.platform-card.failed .platform-status {
  color: #ff4d4f;
}

.platform-actions {
  font-size: 13px;
}

.draft-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px;
}

.draft-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.draft-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 17px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.draft-header p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.draft-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.draft-item {
  min-height: 72px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: #fff;
}

.draft-item.syncing {
  border-color: #1677ff;
  background: rgba(22, 119, 255, 0.04);
}

.draft-item.success {
  border-color: #22c55e;
  background: rgba(34, 197, 94, 0.06);
}

.draft-item.failed {
  border-color: #ff4d4f;
  background: rgba(255, 77, 79, 0.05);
}

.draft-platform {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 700;
}

.draft-message {
  color: var(--color-text-secondary);
  font-size: 13px;
  margin-top: 6px;
}

.draft-item.success .draft-message {
  color: #16a34a;
  font-weight: 600;
}

.draft-item.failed .draft-message {
  color: #ff4d4f;
}

.guide-sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 86px;
  height: fit-content;
}

.guide-card {
  padding: 18px;
}

.guide-card ol {
  padding-left: 20px;
  margin: 16px 0;
  color: var(--color-text-secondary);
  line-height: 1.9;
  font-size: 13px;
}

.guide-card.compact {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.extension-state {
  border-radius: var(--radius-md);
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 700;
}

.extension-state.ok {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.1);
}

.extension-state.warn {
  color: #d97706;
  background: rgba(245, 158, 11, 0.12);
}

@media (max-width: 1180px) {
  .publish-shell {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .guide-sidebar {
    grid-column: 1 / -1;
    position: static;
  }

  .platform-grid,
  .content-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 780px) {
  .publish-page {
    padding: 12px;
  }

  .publish-shell,
  .content-grid,
  .platform-grid {
    grid-template-columns: 1fr;
  }

  .article-sidebar,
  .guide-sidebar {
    position: static;
    height: auto;
  }

  .main-header,
  .platform-toolbar,
  .draft-header {
    flex-direction: column;
  }
}
</style>
