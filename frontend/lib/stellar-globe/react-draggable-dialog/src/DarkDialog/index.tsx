import { Fragment, useCallback, useMemo, useRef } from 'react'
import { Dialog, DialogHandle, DialogProps } from '../Dialog'
import styles from './style.module.scss'


const classNames = {
  dialog: styles.dialog,
  titlebar: styles.titlebar,
  content: styles.content,
  active: styles.active,
}

const {
  appear,
  appearActive,
  appearDone,
  enter,
  enterActive,
  enterDone,
  exit,
  exitActive,
  exitDone,
} = styles

const fadeClassNames = {
  appear,
  appearActive,
  appearDone,
  enter,
  enterActive,
  enterDone,
  exit,
  exitActive,
  exitDone,
}

type Props = Omit<DialogProps, 'classNames' | 'fadeClassNames' | 'fadeDuration'> & {
  onCloseButtonClick?: () => void
  resizeButton?: boolean
}

export function DarkDialog({
  title: rawTitle,
  onCloseButtonClick,
  resizeButton,
  ...rests
}: Props) {

  const autoResize = useCallback(() => {
    dialog.current?.autoResize()
  }, [])

  const title = useMemo(() => {
    if (onCloseButtonClick) {
      return (
        <Fragment>
          <div className={styles.titlebarText}>
            {rawTitle}
          </div>
          {resizeButton &&
            <button
              className={styles.titlebarCloseButton}
              data-no-dnd onClick={autoResize}>
              +
            </button>
          }
          <button
            className={styles.titlebarCloseButton}
            data-no-dnd onClick={onCloseButtonClick}>
            &times;
          </button>
        </Fragment>
      )
    }
    else {
      return rawTitle
    }
  }, [autoResize, onCloseButtonClick, rawTitle, resizeButton])

  const dialog = useRef<DialogHandle>(null)

  return (
    <Dialog
      ref={dialog}
      classNames={classNames}
      title={title}
      fadeClassNames={fadeClassNames}
      fadeDuration={200}
      {...rests}
    />
  )
}
