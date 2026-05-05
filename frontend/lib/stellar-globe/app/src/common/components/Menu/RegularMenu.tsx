import { Menu } from '@szhsin/react-menu'
import classNames from 'classnames'
import { ReactElement, ReactNode, useMemo } from 'react'
import { useMenuContainer } from './MenuContext'
import styles from './styles.module.scss'


type Props = Omit<Parameters<typeof Menu>[0], 'menuButton'> & {
  renderMenuButton?: (state: { active: boolean }) => ReactNode
  renderMenuButtonContents?: (state: { active: boolean }) => ReactNode
}


export function RegularMenu({
  renderMenuButton,
  renderMenuButtonContents,
  ...props
}: Props) {
  const container = useMenuContainer()
  const portal = useMemo(() => container && { target: container }, [container])

  if (!!renderMenuButton === !!renderMenuButtonContents) {
    throw new Error(`Either renderMenuButton or renderMenuButtonContents must be specified.`)
  }

  const menuButton = ({ open }: { open: boolean }): ReactElement => {
    if (renderMenuButton) {
      return renderMenuButton({ active: open }) as ReactElement
    }
    else {
      return (
        <button data-no-dnd className={classNames(styles.hoverMenuButton, open && styles.active)}>
          {renderMenuButtonContents!({ active: open })}
        </button>
      )
    }
  }

  return (
    <Menu
      {...props}
      menuButton={menuButton}
      submenuOpenDelay={0}
      submenuCloseDelay={0}
      theming='dark'
      overflow='auto'
      portal={portal}
      position='anchor'
    />
  )
}
