import { Fragment, useRef } from 'react'
import { CSSTransition } from 'react-transition-group'
import { MenuBar } from '../../common/components/Menu/MenuBar'
import { useAppContext } from '../context'
import { CommonMenu } from '../features/common/CommonMenu'
import { DevelMenu } from '../features/devel/DevelMenu'
import { DialogsMenu } from '../features/dialogs/DialogsMenu'
import { HistoryMenu } from '../features/history/HistoryMenu'
import { ViewMenu } from '../features/view/ViewMenu'
import { DatasetMenu } from './DatasetMenu'
import { ToolsMenu } from './ToolsMenu'
import styles from './styles.module.scss'
import { useAppSelector } from '../store/hooks'


export default function MainMenu() {
  const active = useAppSelector(state => state.common.active)
  const nodeRef = useRef(null)

  return (
    <Fragment>
      <CSSTransition
        in={active}
        timeout={200}
        nodeRef={nodeRef}
        mountOnEnter
        unmountOnExit
        appear
        classNames={{
          appear: styles.enter,
          appearActive: styles.enterActive,
          enter: styles.enter,
          enterActive: styles.enterActive,
          exit: styles.exit,
          exitActive: styles.exitActive,
        }}
      >
        <MenuBar ref={nodeRef} className={styles.menuBar}>
          <CommonMenu />
          <ViewMenu />
          <DatasetMenu />
          <ToolsMenu />
          <HistoryMenu />
          <DialogsMenu />
          <DevelMenu />
        </MenuBar >
      </CSSTransition>
    </Fragment>
  )
}
