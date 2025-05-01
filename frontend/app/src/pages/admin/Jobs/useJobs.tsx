import { useCallback, useMemo, useState } from "react"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus } from "../../../store/api/openapi"
import { websocketUrl } from "../../../utils/websocket"


export function useJobs() {
  const [jobs, setJobs] = useState<QuicklookStatus[]>([])
  const wsUrl = useMemo(() => websocketUrl(`./api/quicklooks.ws`), [])

  useWebsocket({
    url: wsUrl,
    onMessage: useCallback(e => {
      const msg: QuicklookStatus[] = JSON.parse(e.data)
      setJobs(msg)
    }, [setJobs]),
  })

  return jobs
}
