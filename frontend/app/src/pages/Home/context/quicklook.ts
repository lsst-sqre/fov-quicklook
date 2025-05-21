import { useCallback, useEffect, useRef, useState } from "react"
import { env } from "../../../env"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus, useCreateQuicklookMutation, useShowQuicklookMetadataQuery } from "../../../store/api/openapi"
import { useAppSelector } from "../../../store/hooks"



export function useQuicklookStatus() {
  const id = useAppSelector(state => state.home.currentQuicklook)
  const [status, setStatus] = useState<{ [id: string]: QuicklookStatus | null }>({})
  const ready = id !== undefined ? ((status[id]?.phase ?? 0) >= 2) : false
  const { data: metadata, isFetching: metadataIsFeatching } = useShowQuicklookMetadataQuery({ id: id ?? '-' }, { skip: !ready })
  const changeCount = useRef(0)

  const { reconnect } = useWebsocket({
    path: `${env.baseUrl}/api/quicklooks/${id}/status.ws`,
    onMessage: useCallback(e => {
      if (id !== undefined) {
        const msg: QuicklookStatus | null = JSON.parse(e.data)
        setStatus({ ...status, [id]: msg })
      }
    }, [id, status]),
    skip: id === undefined || ready,
  })

  const [callCreateQuicklookApi,] = useCreateQuicklookMutation()

  const createQuicklook = useCallback(async () => {
    if (id !== undefined) {
      await callCreateQuicklookApi({ quicklookCreateFrontend: { id } })
      reconnect()
    }
  }, [callCreateQuicklookApi, id, reconnect])

  useEffect(() => {
    createQuicklook()
  }, [createQuicklook])

  useEffect(() => {
    if (id !== undefined) {
      changeCount.current += 1
    }
  }, [id])

  return {
    id,
    status: id ? status[id] : null,
    metadata: ready && !metadataIsFeatching && metadata || undefined,
    ready,
    changeCount: () => changeCount.current,
  }
}
