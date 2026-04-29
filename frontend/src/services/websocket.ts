/**
 * WebSocket service for real-time job and dashboard updates.
 * Constructs ws/wss URL from window.location to work correctly
 * behind reverse proxies.
 */

type MessageHandler = (data: unknown) => void

function buildWsUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  return `${protocol}://${host}${path}`
}

export class JobWebSocket {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private handlers: MessageHandler[] = []
  private jobId: string
  private closed = false

  constructor(jobId: string) {
    this.jobId = jobId
  }

  connect(): void {
    const url = buildWsUrl(`/ws/jobs/${this.jobId}`)
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handlers.forEach((h) => h(data))
      } catch {
        // ignore malformed messages
      }
    }

    this.ws.onclose = () => {
      if (!this.closed) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }

  disconnect(): void {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }
}

export class DashboardWebSocket {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private handlers: MessageHandler[] = []
  private closed = false

  connect(): void {
    const url = buildWsUrl('/ws/dashboard')
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handlers.forEach((h) => h(data))
      } catch {
        // ignore malformed messages
      }
    }

    this.ws.onclose = () => {
      if (!this.closed) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }

  disconnect(): void {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }
}
