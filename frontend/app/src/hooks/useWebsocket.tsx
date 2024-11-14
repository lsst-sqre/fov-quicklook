import { useCallback, useEffect, useState } from "react"

type UseWebsocketProps = {
  url: string
  onMessage: (e: MessageEvent) => void
  onClose?: (e: CloseEvent) => void
  skip?: boolean
}


export function useWebsocket({
  url,
  onMessage,
  onClose,
  skip = false,
}: UseWebsocketProps) {
  const [connected, setConnected] = useState(false)
  const [reconnectCount, setReconnectCount] = useState(0)

  useEffect(() => {
    if (!skip) {
      console.log(`connecting to ${url}`)
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
  }, [onClose, onMessage, url, reconnectCount, skip])

  const reconnect = useCallback(() => {
    setReconnectCount(_ => _ + 1)
  }, [])

  return {
    connected,
    reconnect,
  }
}
