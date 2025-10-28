import { createContext, ReactNode, useCallback, useContext, useEffect, useRef } from "react"
import { useGetQuicklookMetadata_WS_Query } from "../../../store/api/base"
import { QuicklookMetadata, useCreateQuicklookMutation, useVoteQuicklookMutation, useUnvoteQuicklookMutation } from "../../../store/api/openapi"
import { useAppSelector } from "../../../store/hooks"

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
  const previousId = useRef<string | undefined>(undefined)

  const [createQuicklook] = useCreateQuicklookMutation()
  const [voteQuicklook] = useVoteQuicklookMutation()
  const [unvoteQuicklook] = useUnvoteQuicklookMutation()

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

  useEffect(() => {
    if (previousId.current && previousId.current !== currentId) {
      unvoteQuicklook({ visitName: previousId.current }).catch(err => {
        console.warn(`Failed to unvote ${previousId.current}:`, err)
      })
    }

    if (currentId) {
      voteQuicklook({ visitName: currentId }).catch(err => {
        console.warn(`Failed to vote ${currentId}:`, err)
      })
    }

    previousId.current = currentId
  }, [currentId, voteQuicklook, unvoteQuicklook])

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (currentId) {
        const blob = new Blob([JSON.stringify({})], { type: 'application/json' })
        navigator.sendBeacon(`/api/quicklooks/${currentId}/unvote`, blob)
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [currentId])

  return {
    id: currentId,
    metadata,
    ready,
    changeCount: () => changeCount.current,
  }
}
