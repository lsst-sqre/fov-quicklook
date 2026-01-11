import { useEffect, useRef } from 'react'
import { useHealthzQuery } from '../store/api/openapi'


const CHECK_INTERVAL = 30_000


/**
 * Coordinator IDを定期的にチェックし、変更があったらページをリロードする。
 * 
 * GeneratorがCoordinator再起動を検知して自動再起動するのと同様、
 * FrontendもCoordinator再起動時に再起動する必要がある。
 */
export function useCoordinatorIdMonitor() {
  const { data, refetch } = useHealthzQuery(undefined, {
    pollingInterval: CHECK_INTERVAL,
  })
  const initialCoordinatorIdRef = useRef<string | null>(null)

  useEffect(() => {
    const coordinatorId = data?.coordinator_id
    if (coordinatorId === undefined) return

    if (initialCoordinatorIdRef.current === null) {
      initialCoordinatorIdRef.current = coordinatorId
      return
    }

    if (coordinatorId !== initialCoordinatorIdRef.current) {
      console.warn(
        `Coordinator ID changed from ${initialCoordinatorIdRef.current} to ${coordinatorId}. Reloading...`
      )
      window.location.reload()
    }
  }, [data?.coordinator_id, refetch])
}
