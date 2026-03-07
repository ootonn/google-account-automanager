import { defineStore } from 'pinia'
import { ref } from 'vue'

function getDefaultWebSocketUrl() {
  if (typeof window === 'undefined') {
    return 'ws://127.0.0.1:8000/ws'
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

const webSocketUrl = import.meta.env.VITE_WS_URL || getDefaultWebSocketUrl()

export const useWebSocket = defineStore('websocket', () => {
  const connected = ref(false)
  const logs = ref([])
  const taskProgress = ref(null)
  const accountsProgress = ref({})
  let ws = null
  let heartbeatTimer = null
  let reconnectTimer = null
  let shouldReconnect = true

  function clearHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      return
    }

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 3000)
  }

  function connect() {
    shouldReconnect = true

    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    ws = new WebSocket(webSocketUrl)

    ws.onopen = () => {
      connected.value = true
      console.log('[WS] 已连接')
      clearHeartbeat()
      heartbeatTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
    }

    ws.onclose = () => {
      connected.value = false
      clearHeartbeat()
      console.log('[WS] 已断开')
      if (shouldReconnect) {
        scheduleReconnect()
      }
    }

    ws.onerror = (err) => {
      console.error('[WS] 错误:', err)
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return

      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch (e) {
        console.error('[WS] 解析消息失败:', e)
      }
    }
  }

  function handleMessage(msg) {
    if (msg.type === 'task_progress') {
      taskProgress.value = msg.data
      if (msg.data.status === 'completed' || msg.data.status === 'failed') {
        setTimeout(() => {
          accountsProgress.value = {}
        }, 5000)
      }
    } else if (msg.type === 'account_progress') {
      const data = msg.data
      accountsProgress.value = {
        ...accountsProgress.value,
        [data.email]: {
          email: data.email,
          status: data.status,
          currentTask: data.current_task,
          message: data.message,
          total: data.total,
          completed: data.completed,
          failed: data.failed,
        },
      }
    } else if (msg.type === 'log') {
      logs.value.unshift({
        ...msg.data,
        time: new Date().toLocaleTimeString(),
      })
      if (logs.value.length > 100) {
        logs.value = logs.value.slice(0, 100)
      }
    }
  }

  function disconnect() {
    shouldReconnect = false

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    clearHeartbeat()
    if (ws) {
      const socket = ws
      ws = null
      socket.close()
    }
  }

  function clearLogs() {
    logs.value = []
  }

  function clearAccountsProgress() {
    accountsProgress.value = {}
  }

  return {
    connected,
    logs,
    taskProgress,
    accountsProgress,
    connect,
    disconnect,
    clearLogs,
    clearAccountsProgress,
  }
})
