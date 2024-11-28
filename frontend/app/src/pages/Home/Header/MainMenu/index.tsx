import { Menu, MenuButton, MenuDivider, MenuItem } from "@szhsin/react-menu"
import { MaterialSymbol } from "../../../../components/MaterialSymbol"
import { useResetView } from "../../context"
import { useCallback } from "react"
import { useAppDispatch, useAppSelector } from "../../../../store/hooks"
import { homeSlice } from "../../../../store/features/homeSlice"

export function MainMenu() {
  const lineProfilerEnabled = useAppSelector(state => state.home.lineProfiler.enabled)
  const dispatchc = useAppDispatch()
  const resetVeiw = useResetView()
  const toggleLineProfiler = useCallback(() => {
    dispatchc(homeSlice.actions.toggleLineProfiler())
  }, [dispatchc])

  return (
    <div>
      <Menu menuButton={<MenuButton><MaterialSymbol symbol="menu" /></MenuButton>} theming="dark"  >
        <MenuItem onClick={() => resetVeiw()}>Re-Center</MenuItem>
        <MenuDivider />
        <MenuItem type="checkbox" checked={lineProfilerEnabled} onClick={toggleLineProfiler}>Line Profiler</MenuItem>
      </Menu>
    </div>
  )
}
