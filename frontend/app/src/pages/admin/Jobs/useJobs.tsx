import { useCallback, useState } from "react"
import { env } from "../../../env"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus } from "../../../store/api/openapi"


export function useJobs() {
  const [jobs, setJobs] = useState<QuicklookStatus[]>([])

  useWebsocket({
    path: `${env.baseUrl}/api/quicklooks.ws`,
    onMessage: useCallback(e => {
      const msg: QuicklookStatus[] = JSON.parse(e.data)
      setJobs(msg)
    }, [setJobs]),
  })

  return jobs
}
