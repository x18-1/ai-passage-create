import { onMounted, onUnmounted, ref } from 'vue'

export interface HotspotWsEvent {
  type: 'hotspot_new' | 'pong'
  importance?: string
  title?: string
  source?: string
  keywordText?: string
}

export function useHotspotWs(onHotspotNew?: (event: HotspotWsEvent) => void) {
  const isConnected = ref(false)
  let ws: WebSocket | null = null
  let pingInterval: ReturnType<typeof setInterval> | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.DEV ? 'localhost:8567' : location.host
    ws = new WebSocket(`${protocol}//${host}/api/hotspot/ws`)

    ws.onopen = () => {
      isConnected.value = true
      pingInterval = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send('{"type":"ping"}')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const data: HotspotWsEvent = JSON.parse(event.data)
        if (data.type === 'hotspot_new') {
          onHotspotNew?.(data)
        }
      } catch {
        // ignore malformed
      }
    }

    ws.onclose = () => {
      isConnected.value = false
      if (pingInterval) clearInterval(pingInterval)
      // 5秒后重连
      reconnectTimeout = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimeout) clearTimeout(reconnectTimeout)
    if (pingInterval) clearInterval(pingInterval)
    ws?.close()
    ws = null
    isConnected.value = false
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { isConnected }
}
