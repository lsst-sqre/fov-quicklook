import { useEffect } from "react"
import { useListHipsRepositoriesQuery } from "../../store/api/openapi"
import { hipsSlice } from "../../store/features/hipsSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { HipsViewer } from "./HipsViewer"
import styles from './styles.module.scss'

export function HipsPage() {
  return (
    <div style={{ height: '100%', position: 'relative' }}>
      <HipsViewer />
      <HipsConfig />
    </div>
  )
}


function HipsConfig() {
  const { data: repositories } = useListHipsRepositoriesQuery()
  const dispatch = useAppDispatch()
  const repository = useAppSelector((state) => state.hips.repository)

  useEffect(() => {
    if (repositories && repositories.length > 0) {
      dispatch(hipsSlice.actions.setRepository(repositories[0].name))
    }
  }, [dispatch, repositories])

  return (
    <div className={styles.config}>
      <select
        value={repository}
        onChange={(e) => dispatch(hipsSlice.actions.setRepository(e.target.value))}
      >
        {(repositories ?? []).map((repo) => (
          <option key={repo.name} value={repo.name}>
            {repo.name}
          </option>
        ))}
      </select>
    </div>
  )
}
