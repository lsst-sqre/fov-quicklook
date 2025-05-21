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
      ws.onopen = () => {
        setConnected(true)
      }
      ws.onmessage = e => {
        onMessage(e)
      }
      ws.onclose = e => {
        setConnected(false)
        onClose?.(e)
      }
      return () => {
        ws.close()
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
