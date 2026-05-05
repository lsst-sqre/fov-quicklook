import { ControlledMenu, useClick, useHover, useMenuState } from '@szhsin/react-menu'
import classNames from 'classnames'
import { Fragment, MutableRefObject, ReactNode, useEffect, useMemo, useRef } from 'react'
import { useMenuContainer } from './MenuContext'
import styles from './styles.module.scss'


const closers = new Map<MutableRefObject<null>, () => void>()


type Props = {
  renderMenuButton?: (state: { active: boolean }) => ReactNode
  renderMenuButtonContents?: (state: { active: boolean }) => ReactNode
  children: ReactNode
  className?: string
} & Parameters<typeof ControlledMenu>[0]


export function HoverMenu({ className, children, renderMenuButton, renderMenuButtonContents, ...menuProps }: Props) {
  const anchorRef = useRef(null)
  const [menuState, toggle] = useMenuState()
  const clickProps = useClick(menuState.state, toggle)
  const { anchorProps, hoverProps } = useHover(menuState.state, toggle, { openDelay: 0, closeDelay: 1000 })

  if (!!renderMenuButton === !!renderMenuButtonContents) {
    throw new Error(`Either renderMenuButton or renderMenuButtonContents must be specified.`)
  }

  useEffect(() => {
    closers.set(anchorRef, () => toggle(false))
    return () => {
      closers.delete(anchorRef)
    }
  }, [toggle])

  useEffect(() => {
    if (menuState.state === 'open') {
      for (const [ref, close] of closers) {
        if (ref !== anchorRef) {
          close()
        }
      }
    }
  }, [menuState.state])

  const container = useMenuContainer()
  const portal = useMemo(() => container && { target: container }, [container])

  return (
    <Fragment>
      <div
        ref={anchorRef}
        {...anchorProps}
        {...clickProps}
        className={className}
      >
        {renderMenuButton?.({ active: menuState.state === 'open' })}
        {renderMenuButtonContents && (
          <button className={classNames(styles.hoverMenuButton, menuState.state === 'open' && styles.active)}>
            {renderMenuButtonContents({ active: menuState.state === 'open' })}
          </button>
        )}
      </div>
      <ControlledMenu
        overflow='auto'
        {...hoverProps}
        {...menuState}
        theming='dark'
        anchorRef={anchorRef}
        onClose={() => toggle(false)}
        submenuOpenDelay={0}
        submenuCloseDelay={0}
        portal={portal}
        {...menuProps}
      >
        {children}
      </ControlledMenu>
    </Fragment>
  )
}
