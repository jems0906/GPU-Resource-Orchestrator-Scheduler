import { useEffect, useRef, useState } from 'react'
import { JobWebSocket, DashboardWebSocket } from '@/services/websocket'

export function useJobWebSocket(jobId: string) {
  const [data, setData] = useState<unknown>(null)
  const wsRef = useRef<JobWebSocket | null>(null)

  useEffect(() => {
    if (!jobId) return
    const ws = new JobWebSocket(jobId)
    wsRef.current = ws
    const unsubscribe = ws.onMessage((msg) => setData(msg))
    ws.connect()
    return () => {
      unsubscribe()
      ws.disconnect()
    }
  }, [jobId])

  return data
}

export function useDashboardWebSocket() {
  const [data, setData] = useState<unknown>(null)
  const wsRef = useRef<DashboardWebSocket | null>(null)

  useEffect(() => {
    const ws = new DashboardWebSocket()
    wsRef.current = ws
    const unsubscribe = ws.onMessage((msg) => setData(msg))
    ws.connect()
    return () => {
      unsubscribe()
      ws.disconnect()
    }
  }, [])

  return data
}
