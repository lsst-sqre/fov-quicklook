import { useCallback, useEffect, useMemo, useState } from "react"
import { websocketUrl } from "../utils/websocket"

type UseWebsocketProps = {
  path: string
  onMessage: (e: MessageEvent) => void
  onClose?: (e: CloseEvent) => void
  skip?: boolean
}

export function useWebsocket({
  path,
  onMessage,
  onClose,
  skip = false,
}: UseWebsocketProps) {
  const [connected, setConnected] = useState(false)
  const [reconnectCount, setReconnectCount] = useState(0)
  const url = useMemo(() => websocketUrl(path), [path])

  useEffect(() => {
    if (!skip) {
      const ws = new WebSocket(url)
      const status = { closing: false, connected: false }
      ws.onopen = () => {
        setConnected(true)
        status.connected = true
        if (status.closing) {
          ws.close()
        }
      }
      ws.onmessage = e => {
        onMessage(e)
      }
      ws.onclose = e => {
        setConnected(false)
        onClose?.(e)
      }
      return () => {
        if (status.connected) {
          ws.close()
        }
        status.closing = true
      }
    }
  }, [onClose, onMessage, reconnectCount, skip, url])

  const reconnect = useCallback(() => {
    setReconnectCount(_ => _ + 1)
  }, [])

  return {
    connected,
    reconnect,
  }
}
