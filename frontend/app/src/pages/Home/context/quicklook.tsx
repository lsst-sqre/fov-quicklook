import { createContext, ReactNode, useCallback, useContext, useEffect, useRef } from "react"
import { useGetQuicklookMetadata_WS_Query } from "../../../store/api/base"
import { QuicklookMetadata, useCreateQuicklookMutation } from "../../../store/api/openapi"
import { useAppSelector } from "../../../store/hooks"
import { useQuicklookVoting } from "../../../hooks/useQuicklookVoting"

type QuicklookContextType = {
  metadata: QuicklookMetadata | undefined
  ready: boolean
}

const QuicklookContext = createContext<QuicklookContextType | undefined>(undefined)

export function QuicklookMetadataProvider({ children }: { children: ReactNode }) {
  const visitName = useAppSelector(state => state.home.currentQuicklook)
  const { data: metadata } = useGetQuicklookMetadata_WS_Query({ visitName: visitName! }, { skip: !visitName })

  // コンテキスト値を構築
  const contextValue: QuicklookContextType = {
    metadata,
    ready: metadata?.type === 'ready',
  }

  return (
    <QuicklookContext.Provider value={contextValue}>
      {children}
    </QuicklookContext.Provider>
  )
}

function useQuicklookContext() {
  const context = useContext(QuicklookContext)
  if (context === undefined) {
    throw new Error("useQuicklookContext must be used within a QuicklookStatusProvider")
  }
  return context
}

export function useQuicklookMetadata() {
  const currentId = useAppSelector(state => state.home.currentQuicklook)
  const { metadata, ready } = useQuicklookContext()
  const changeCount = useRef(0)

  const [createQuicklook] = useCreateQuicklookMutation()

  useQuicklookVoting(currentId)

  const initializeQuicklook = useCallback(async () => {
    if (currentId) {
      await createQuicklook({ createQuicklookRequest: { visit: currentId } })
    }
  }, [createQuicklook, currentId])

  useEffect(() => {
    initializeQuicklook()
  }, [initializeQuicklook])

  useEffect(() => {
    if (currentId) {
      changeCount.current += 1
    }
  }, [currentId])

  return {
    id: currentId,
    metadata,
    ready,
    changeCount: () => changeCount.current,
  }
}
