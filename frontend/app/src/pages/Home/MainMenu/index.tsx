import { angle } from "@stellar-globe/stellar-globe"
import { Menu, MenuButton, MenuDivider, MenuItem } from "@szhsin/react-menu"
import { useCallback } from "react"
import { MaterialSymbol } from "../../../components/MaterialSymbol"
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useGlobe, useResetView } from "../context"
import styles from './styles.module.scss'

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
  const showFrame = useAppSelector(state => state.home.showFrame)
  const toggleFrame = useCallback(() => {
    dispatch(homeSlice.actions.setShowFrame(!showFrame))
  }, [dispatch, showFrame])

  return (
    <div>
      <Menu menuButton={<MenuButton className={styles.menuButton} ><MaterialSymbol symbol="menu" /></MenuButton>} theming="dark"  >
        <MenuItem onClick={() => resetVeiw()}>Re-Center</MenuItem>
        <MenuItem onClick={() => rorate90()} >Rotate 90&deg;</MenuItem>
        <MenuDivider />
        <MenuItem type="checkbox" checked={lineProfilerEnabled} onClick={toggleLineProfiler}>Line Profiler</MenuItem>
        <MenuItem type="checkbox" checked={showFrame} onClick={toggleFrame}>Frame</MenuItem>
      </Menu>
    </div>
  )
}
