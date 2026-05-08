import { onMounted, onUnmounted, ref } from 'vue'

export interface HotspotWsEvent {
  type: 'hotspot_new' | 'pong'
  importance?: string
  title?: string
  source?: string
  keywordText?: string
}

// Module-level singleton — one connection for the whole app lifetime
const isConnected = ref(false)
const callbacks = new Set<(event: HotspotWsEvent) => void>()
let ws: WebSocket | null = null
let pingInterval: ReturnType<typeof setInterval> | null = null
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  if (reconnectTimeout) { clearTimeout(reconnectTimeout); reconnectTimeout = null }

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.DEV ? 'localhost:8567' : location.host
  ws = new WebSocket(`${protocol}//${host}/api/hotspot/ws`)

  ws.onopen = () => {
    isConnected.value = true
    pingInterval = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) ws.send('{"type":"ping"}')
    }, 30000)
  }

  ws.onmessage = (event) => {
    try {
      const data: HotspotWsEvent = JSON.parse(event.data)
      if (data.type === 'hotspot_new') {
        callbacks.forEach((cb) => cb(data))
      }
    } catch { /* ignore malformed */ }
  }

  ws.onclose = () => {
    isConnected.value = false
    if (pingInterval) { clearInterval(pingInterval); pingInterval = null }
    ws = null
    reconnectTimeout = setTimeout(connect, 5000)
  }

  ws.onerror = () => { ws?.close() }
}

/** Call once from App.vue onMounted to establish the persistent connection. */
export function initHotspotWs() {
  connect()
}

/**
 * Register a callback that fires on each hotspot_new event.
 * The WebSocket is managed at module level — this composable never creates
 * or destroys the connection.
 */
export function useHotspotWs(onHotspotNew?: (event: HotspotWsEvent) => void) {
  if (onHotspotNew) {
    onMounted(() => callbacks.add(onHotspotNew))
    onUnmounted(() => callbacks.delete(onHotspotNew))
  }
  return { isConnected }
}
