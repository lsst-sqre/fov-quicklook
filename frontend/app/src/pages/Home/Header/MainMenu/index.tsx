import { Menu, MenuButton, MenuDivider, MenuItem } from "@szhsin/react-menu"
import { MaterialSymbol } from "../../../../components/MaterialSymbol"
import { useGlobe, useResetView } from "../../context"
import { useCallback } from "react"
import { useAppDispatch, useAppSelector } from "../../../../store/hooks"
import { homeSlice } from "../../../../store/features/homeSlice"
import { angle } from "@stellar-globe/stellar-globe"

export function MainMenu() {
  const lineProfilerEnabled = useAppSelector(state => state.home.lineProfiler.enabled)
  const dispatch = useAppDispatch()
  const resetVeiw = useResetView()
  const toggleLineProfiler = useCallback(() => {
    dispatch(homeSlice.actions.toggleLineProfiler())
  }, [dispatch])
  const globe = useGlobe()
  const rorate90 = () => {
    if (globe) {
      globe.camera.jumpTo({ roll: globe.camera.roll + angle.deg2rad(90) }, { duration: 400 })
    }
  }

  return (
    <div>
      <Menu menuButton={<MenuButton><MaterialSymbol symbol="menu" /></MenuButton>} theming="dark"  >
        <MenuItem onClick={() => resetVeiw()}>Re-Center</MenuItem>
        <MenuItem onClick={() => rorate90()} >Rotate 90&deg;</MenuItem>
        <MenuDivider />
        <MenuItem type="checkbox" checked={lineProfilerEnabled} onClick={toggleLineProfiler}>Line Profiler</MenuItem>
      </Menu>
    </div>
  )
}
