import { GlobePointerEvent, SkyCoord } from "@stellar-globe/stellar-globe"
import { ControlledMenu } from "@szhsin/react-menu"
import { Fragment, ReactNode, useCallback, useMemo, useState } from "react"
// import { useMenuContainer } from "../../common/components/Menu/MenuContext"
import { PointerLayer$ } from "./PointerLayer"


type Props = {
  render: (openedAt: SkyCoord) => ReactNode
  onOpen?: () => void
}


export const ContextMenuWithClickedCoord = ({
  render,
  onOpen,
}: Props) => {
  const [openedAt, setOpenedAt] = useState<SkyCoord>()
  const onContextMenu: (e: GlobePointerEvent) => void = useCallback((e) => {
    onOpen?.()
    e.originalEvent({
      mouse: e2 => e2.preventDefault(),
      touch: e2 => e2.preventDefault(),
    })
    setOpenedAt(e.coord)
    setAnchorPoint({ x: e.clientX, y: e.clientY })
    setOpen(true)
  }, [onOpen])
  const [isOpen, setOpen] = useState(false)
  const [anchorPoint, setAnchorPoint] = useState({ x: 0, y: 0 })
  // const container = useMenuContainer()
  // const portal = useMemo(() => container && { target: container }, [container])

  return (
    <Fragment>
      {openedAt && (
        <ControlledMenu
          theming='dark'
          anchorPoint={anchorPoint}
          state={isOpen ? 'open' : 'closed'}
          onClose={() => setOpen(false)}
          submenuOpenDelay={0}
          submenuCloseDelay={0}
          // portal={portal}
          overflow='auto'
        >
          {render(openedAt)}
        </ControlledMenu>
      )}
      <PointerLayer$ onContextMenu={onContextMenu} />
    </Fragment>
  )
}
