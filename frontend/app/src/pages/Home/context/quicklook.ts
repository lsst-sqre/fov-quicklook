import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus, useCreateQuicklookMutation, useShowQuicklookMetadataQuery } from "../../../store/api/openapi"
import { useAppSelector } from "../../../store/hooks"
import { websocketUrl } from "../../../utils/websocket"



export function useQuicklookStatus() {
  const id = useAppSelector(state => state.home.currentQuicklook)
  const [status, setStatus] = useState<{ [id: string]: QuicklookStatus | null }>({})
  const ready = id !== undefined ? ((status[id]?.phase ?? 0) >= 2) : false
  const wsUrl = useMemo(() => websocketUrl(`./api/quicklooks/${id}/status.ws`), [id])
  const { data: metadata, isFetching: metadataIsFeatching } = useShowQuicklookMetadataQuery({ id: id ?? '-' }, { skip: !ready })
  const changeCount = useRef(0)

  const { reconnect } = useWebsocket({
    url: wsUrl,
    onMessage: useCallback(e => {
      if (id !== undefined) {
        const msg: QuicklookStatus | null = JSON.parse(e.data)
        setStatus({ [id]: msg })
      }
    }, [id]),
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
