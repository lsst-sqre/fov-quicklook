import { useRef } from 'react'
import { CSSTransition, TransitionGroup } from 'react-transition-group'
import { useGetQuicklooksStatusQuery } from '../../store/api/base'
import { JobStatusVisualizer } from '../JobStatusVisualizer/JobStatusVisualizer'
import styles from './styles.module.scss'

export function JobList({ highlightKey }: { highlightKey?: string } = {}) { 
  const { data: statusList } = useGetQuicklooksStatusQuery()
  const nodeRefs = useRef<Map<string, React.RefObject<HTMLDivElement>>>(new Map())

  const getNodeRef = (key: string) => {
    if (!nodeRefs.current.has(key)) {
      nodeRefs.current.set(key, { current: null })
    }
    return nodeRefs.current.get(key)!
  }

  return (
    <div className={styles.container}>
      <TransitionGroup>
        {statusList && Object.entries(statusList).map(([key, status]) => (
          <CSSTransition
            key={key}
            timeout={300}
            classNames={{
              enter: styles.itemEnter,
              enterActive: styles.itemEnterActive,
              exit: styles.itemExit,
              exitActive: styles.itemExitActive,
            }}
            nodeRef={getNodeRef(key)}
          >
            <div ref={getNodeRef(key)}>
              <JobStatusVisualizer status={status} isHighlighted={key === highlightKey} />
              <div className={styles.spacer} />
            </div>
          </CSSTransition>
        ))}
      </TransitionGroup>
    </div>
  )
}
