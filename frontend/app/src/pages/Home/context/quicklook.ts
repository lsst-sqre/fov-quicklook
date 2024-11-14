import { useCallback, useEffect, useMemo, useState } from "react"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus, useCreateQuicklookMutation, useShowQuicklookMetadataQuery } from "../../../store/api/openapi"
import { useAppSelector } from "../../../store/hooks"
import { websocketUrl } from "../../../utils/websocket"



export function useQuicklookStatus() {
  const id = useAppSelector(state => state.home.currentQuicklook)
  const [status, setStatus] = useState<{ [id: string]: QuicklookStatus | null }>({})
  const ready = id !== undefined ? (status[id]?.phase === 'ready') : false
  const { data: metadata } = useShowQuicklookMetadataQuery({ id: id ?? '' }, { skip: !ready })
  const wsUrl = useMemo(() => websocketUrl(`./api/quicklooks/${id}/status.ws`), [id])

  const { reconnect } = useWebsocket({
    url: wsUrl,
    onMessage: useCallback(e => {
      if (id !== undefined) {
        const msg: QuicklookStatus | null = JSON.parse(e.data)
        setStatus({ [id]: msg })
      }
    }, [id]),
    skip: id === undefined,
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

  return {
    id,
    status: id ? status[id] : null,
    metadata: ready ? metadata : undefined,
    ready,
  }
}
