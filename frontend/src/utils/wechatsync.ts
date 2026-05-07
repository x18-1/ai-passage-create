import { markdownToHtml } from '@/utils/markdown'

export type SyncerPlatformStatus = 'unknown' | 'authenticated' | 'unauthenticated'
export type SyncerPublishStatus = 'idle' | 'syncing' | 'success' | 'failed'

export interface SyncerAccount {
  type: string
  title: string
  displayName?: string
  icon?: string
  avatar?: string
  uid?: string
  home?: string
  supportTypes?: string[]
}

export interface SyncerPlatform extends SyncerAccount {
  status: SyncerPlatformStatus
  publishStatus: SyncerPublishStatus
  message?: string
  error?: string
  draftLink?: string
}

export interface SyncerArticlePayload {
  title: string
  markdown: string
  cover?: string
}

export interface SyncerTaskUpdateAccount extends SyncerAccount {
  status?: 'pending' | 'uploading' | 'done' | 'failed'
  msg?: string
  error?: string
  editResp?: {
    draftLink?: string
  } | null
}

export interface SyncerTaskUpdate {
  accounts?: SyncerTaskUpdateAccount[]
}

interface WindowSyncer {
  getAccounts: (callback: (result: SyncerAccount[]) => void) => void
  addTask: (
    task: {
      post: {
        title: string
        content: string
        markdown: string
        thumb?: string
      }
      accounts: SyncerAccount[]
    },
    statusHandler: (task: SyncerTaskUpdate) => void,
    callback: (result: unknown) => void
  ) => void
}

declare global {
  interface Window {
    $syncer?: WindowSyncer
    $poster?: WindowSyncer
  }
}

const DEFAULT_TIMEOUT = 15000

const withTimeout = <T>(executor: (resolve: (value: T) => void, reject: (reason?: unknown) => void) => void, timeoutMessage: string): Promise<T> => {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(timeoutMessage))
    }, DEFAULT_TIMEOUT)

    executor(
      (value) => {
        window.clearTimeout(timer)
        resolve(value)
      },
      (reason) => {
        window.clearTimeout(timer)
        reject(reason)
      },
    )
  })
}

export const isWechatsyncAvailable = (): boolean => {
  return typeof window !== 'undefined' && typeof window.$syncer?.getAccounts === 'function'
}

export const getWechatsyncAccounts = async (): Promise<SyncerAccount[]> => {
  if (!isWechatsyncAvailable()) {
    throw new Error('未检测到 Wechatsync Chrome 扩展')
  }

  return withTimeout<SyncerAccount[]>((resolve, reject) => {
    try {
      window.$syncer!.getAccounts((result) => {
        resolve(Array.isArray(result) ? result : [])
      })
    } catch (error) {
      reject(error)
    }
  }, '查询平台登录状态超时，请确认扩展已启用')
}

export const publishWithWechatsync = async (
  article: SyncerArticlePayload,
  accounts: SyncerAccount[],
  onUpdate: (task: SyncerTaskUpdate) => void,
): Promise<unknown> => {
  if (!isWechatsyncAvailable()) {
    throw new Error('未检测到 Wechatsync Chrome 扩展')
  }
  if (accounts.length === 0) {
    throw new Error('请选择至少一个已登录平台')
  }

  return new Promise<unknown>((resolve, reject) => {
    try {
      window.$syncer!.addTask(
        {
          post: {
            title: article.title,
            content: markdownToHtml(article.markdown),
            markdown: article.markdown,
            thumb: article.cover,
          },
          accounts,
        },
        onUpdate,
        (result) => {
          resolve(result)
        },
      )
      window.setTimeout(() => resolve({ submitted: true }), 0)
    } catch (error) {
      reject(error)
    }
  })
}

export const platformFromAccount = (account: SyncerAccount): SyncerPlatform => ({
  ...account,
  status: 'authenticated',
  publishStatus: 'idle',
})
