import { useEffect } from "react"
import { useVoteQuicklookMutation, useUnvoteQuicklookMutation } from "../store/api/openapi"
import { useWatch } from "./useWatch"

export function useQuicklookVoting(visitName: string | undefined) {
  const [voteQuicklook] = useVoteQuicklookMutation()
  const [unvoteQuicklook] = useUnvoteQuicklookMutation()

  useWatch(visitName, (before, after) => {
    if (before) {
      unvoteQuicklook({ visitName: before }).catch(err => {
        console.warn(`Failed to unvote ${before}:`, err)
      })
    }

    if (after) {
      voteQuicklook({ visitName: after }).catch(err => {
        console.warn(`Failed to vote ${after}:`, err)
      })
    }
  })

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (visitName) {
        const blob = new Blob([JSON.stringify({})], { type: 'application/json' })
        navigator.sendBeacon(`/api/quicklooks/${visitName}/unvote`, blob)
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [visitName])
}
