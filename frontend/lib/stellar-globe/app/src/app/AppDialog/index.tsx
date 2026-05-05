import { Dialog, DialogHandle } from '@stellar-globe/react-draggable-dialog'
import { Fragment, ReactNode, useCallback, useMemo, useRef } from 'react'
import { Icon } from '../../common/components/Icon'
import { RegularMenu } from '../../common/components/Menu/RegularMenu'
import { useAppContext } from '../context'
import styles from './style.module.scss'
import { useAppSelector } from '../store/hooks'


type DialogProps = Parameters<typeof Dialog>[0]


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
  menu?: ReactNode
}

export function AppDialog({
  title: rawTitle,
  onCloseButtonClick,
  menu,
  visible,
  rememberPosition,
  resizable = false,
  ...rests
}: Props) {
  const active = useAppSelector(state => state.common.active)
  const dialog = useRef<DialogHandle>(null)
  const showResizeButton = useMemo(
    () => typeof resizable === 'boolean' ? resizable : (resizable.x || resizable.y),
    [resizable],
  )
  const resizeAuto = useCallback(() => {
    dialog.current?.autoResize()
  }, [])

  const title = useMemo(() => {
    return (
      <Fragment>
        <div className={styles.titlebarText}>
          {rawTitle}
        </div>
        <div className={styles.buttons}>
          {menu && (
            <RegularMenu renderMenuButtonContents={() => <Icon type='menu' />}>
              {menu}
            </RegularMenu>
          )}
          {showResizeButton && (
            <button data-no-dnd onClick={resizeAuto}>
              <Icon type='close_fullscreen' />
            </button>
          )}
          {onCloseButtonClick && (
            <button data-no-dnd onClick={onCloseButtonClick}>
              <Icon type='close' />
            </button>
          )}
        </div>
      </Fragment>
    )
  }, [menu, onCloseButtonClick, rawTitle, resizeAuto, showResizeButton])

  return (
    <Dialog
      ref={dialog}
      classNames={classNames}
      title={title}
      fadeClassNames={fadeClassNames}
      fadeDuration={200}
      visible={visible && active}
      rememberPosition={rememberPosition || !active}
      resizable={resizable}
      {...rests}
    />
  )
}
