import { DragEvent, Fragment, ReactNode, useCallback, useRef, useState } from 'react'
import styles from './style.module.scss'
import { CSSTransition } from 'react-transition-group'

type Props = {
  children: ReactNode
  onFileDrop: (filelist: FileList) => void
}


export function DragAndDrop({ children, onFileDrop }: Props) {
  const [active, setActive] = useState(false)

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    setActive(true)
  }, [])

  const onDragLeave = useCallback((e: DragEvent) => {
    setActive(false)
  }, [])

  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault()
    setActive(false)
    const files = e.dataTransfer?.files
    if (files?.length) {
      onFileDrop(files)
    }
  }, [onFileDrop])

  const nodeRef = useRef(null)

  return (
    <Fragment>
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={styles.full}
      >
        {children}
      </div>
      <CSSTransition
        in={active}
        timeout={200}
        nodeRef={nodeRef}
        mountOnEnter
        unmountOnExit
        classNames={{
          enter: styles.fadeEnter,
          enterActive: styles.fadeEnterActive,
          exit: styles.fadeExit,
          exitActive: styles.fadeExitActive,
        }}
      >
        <div ref={nodeRef} className={styles.active} />
      </CSSTransition>

    </Fragment>
  )
}
