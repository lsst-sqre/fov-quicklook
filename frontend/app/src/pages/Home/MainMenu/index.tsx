import { Menu, MenuButton, MenuDivider, MenuItem } from "@szhsin/react-menu"
import { useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { MaterialSymbol } from "../../../components/MaterialSymbol"
import { env } from "../../../env"
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useHomeActions } from "../useHomeActions"

export function MainMenu() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { lineProfilerEnabled, recenter, rotateClockwise, toggleLineProfiler } = useHomeActions()
  const showFrame = useAppSelector(state => state.home.showFrame)
  const toggleFrame = useCallback(() => {
    dispatch(homeSlice.actions.setShowFrame(!showFrame))
  }, [dispatch, showFrame])

  const showCompactStatus = useAppSelector(state => state.home.showCompactStatus)
  const toggleCompactStatus = useCallback(() => {
    dispatch(homeSlice.actions.setShowCompactStatus(!showCompactStatus))
  }, [dispatch, showCompactStatus])

  const showMemoryUsageInCompactStatus = useAppSelector(state => state.home.showMemoryUsageInCompactStatus)
  const toggleMemoryUsageInCompactStatus = useCallback(() => {
    dispatch(homeSlice.actions.setShowMemoryUsageInCompactStatus(!showMemoryUsageInCompactStatus))
  }, [dispatch, showMemoryUsageInCompactStatus])

  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const downloadTimeProfile = useCallback(() => {
    if (!currentQuicklook) return
    const url = `${env.baseUrl}/api/quicklooks/${encodeURIComponent(currentQuicklook)}/time_profile`
    window.open(url, "_blank")
  }, [currentQuicklook])
  const openDataQuery = useCallback(() => {
    navigate("/query?data_type=raw&repository_name=embargo&limit=2")
  }, [navigate])

  return (
    <div>
      <Menu menuButton={<MenuButton><MaterialSymbol symbol="menu" /></MenuButton>} theming="dark"  >
        <MenuItem onClick={recenter}>Re-Center</MenuItem>
        <MenuItem onClick={rotateClockwise} >Rotate 90&deg;</MenuItem>
        <MenuDivider />
        <MenuItem type="checkbox" checked={lineProfilerEnabled} onClick={toggleLineProfiler}>Line Profiler</MenuItem>
        <MenuItem type="checkbox" checked={showFrame} onClick={toggleFrame}>Frame</MenuItem>
        <MenuItem type="checkbox" checked={showCompactStatus} onClick={toggleCompactStatus}>System Status</MenuItem>
        <MenuItem type="checkbox" checked={showMemoryUsageInCompactStatus} onClick={toggleMemoryUsageInCompactStatus}>Show Recoverable Memory</MenuItem>
        <MenuDivider />
        <MenuItem onClick={openDataQuery}>Data Query</MenuItem>
        <MenuItem onClick={downloadTimeProfile} disabled={!currentQuicklook}>Time Profile</MenuItem>
      </Menu>
    </div>
  )
}
