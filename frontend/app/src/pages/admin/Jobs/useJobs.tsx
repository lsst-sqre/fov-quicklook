import { useState, useEffect, useMemo, useCallback } from "react"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus, useListQuicklooksQuery } from "../../../store/api/openapi"
import { websocketUrl } from "../../../utils/websocket"


export function useJobs() {
  const [jobs, setJobs] = useState<QuicklookStatus[]>([])
  const { data } = useListQuicklooksQuery()

  useEffect(() => {
    if (data) {
      setJobs(data)
    }
  }, [data])

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
