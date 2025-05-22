import { useCallback, useEffect, useRef, useState, createContext, useContext, ReactNode } from "react"
import { env } from "../../../env"
import { useWebsocket } from "../../../hooks/useWebsocket"
import { QuicklookStatus, useCreateQuicklookMutation, useShowQuicklookMetadataQuery } from "../../../store/api/openapi"
import { useAppSelector } from "../../../store/hooks"

// 型定義を明確に
type QuicklookContextState = {
  status: QuicklookStatus | null
  ready: boolean
  reconnect: () => void
}

const QuicklookContext = createContext<QuicklookContextState | undefined>(undefined)

export function QuicklookStatusProvider({ children }: { children: ReactNode }) {
  const [statusMap, setStatusMap] = useState<Record<string, QuicklookStatus | null>>({})
  const currentId = useAppSelector(state => state.home.currentQuicklook)
  
  // 準備完了の判定ロジックを単純化
  const isReady = useCallback((id: string | undefined): boolean => {
    if (!id) return false
    const currentStatus = statusMap[id]
    return (currentStatus?.phase ?? 0) >= 2
  }, [statusMap])

  const ready = isReady(currentId)

  // WebSocketの設定
  const { reconnect } = useWebsocket({
    path: `${env.baseUrl}/api/quicklooks/${currentId}/status.ws`,
    onMessage: useCallback(e => {
      if (currentId) {
        const newStatus: QuicklookStatus | null = JSON.parse(e.data)
        setStatusMap(prev => ({ ...prev, [currentId]: newStatus }))
      }
    }, [currentId]),
    skip: !currentId || ready,
  })

  // コンテキスト値を構築
  const contextValue: QuicklookContextState = {
    status: currentId ? statusMap[currentId] : null,
    ready,
    reconnect,
  }

  return (
    <QuicklookContext.Provider value={contextValue}>
      {children}
    </QuicklookContext.Provider>
  )
}

// フック名を短縮し意図を明確に
function useQuicklookContext() {
  const context = useContext(QuicklookContext)
  if (context === undefined) {
    throw new Error("useQuicklookContext must be used within a QuicklookStatusProvider")
  }
  return context
}

// eslint-disable-next-line react-refresh/only-export-components
export function useQuicklookStatus() {
  const currentId = useAppSelector(state => state.home.currentQuicklook)
  const { status, ready, reconnect } = useQuicklookContext()
  const changeCount = useRef(0)
  
  // メタデータの取得
  const { 
    data: metadata, 
    isFetching: isLoadingMetadata 
  } = useShowQuicklookMetadataQuery(
    { id: currentId ?? '-' }, 
    { skip: !ready }
  )

  const [createQuicklook] = useCreateQuicklookMutation()

  // Quicklook作成関数をシンプルに
  const initializeQuicklook = useCallback(async () => {
    if (currentId) {
      await createQuicklook({ quicklookCreateFrontend: { id: currentId } })
      reconnect()
    }
  }, [createQuicklook, currentId, reconnect])

  // 初期化
  useEffect(() => {
    initializeQuicklook()
  }, [initializeQuicklook])

  // IDが変更されたらカウントを増やす
  useEffect(() => {
    if (currentId) {
      changeCount.current += 1
    }
  }, [currentId])

  return {
    id: currentId,
    status,
    metadata: ready && !isLoadingMetadata && metadata || undefined,
    ready,
    changeCount: () => changeCount.current,
  }
}
