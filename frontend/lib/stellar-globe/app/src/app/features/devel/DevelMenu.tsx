import { memo } from "react"
import { Icon } from "../../../common/components/Icon"
import { MenuBarItem } from "../../../common/components/Menu/MenuBarItem"
import { MenuItemWithKeybind } from "../../keybindings/MenuItemWithKeybind"
import { useAppSelector } from "../../store/hooks"

export const DevelMenu = memo(() => {
  const enabled = useAppSelector(state => state.devel.enabled)
  const profilerActive = useAppSelector(state => state.devel.profilerActive)
  const profilerSupported = useAppSelector(state => state.devel.profilerSupported)

  return (
    enabled && (
      <MenuBarItem label={<Icon type="build" />}>
        <MenuItemWithKeybind
          keybind="toggleProfiler"
          disabled={!profilerSupported}
        >{profilerActive ? 'Stop WebGL Profiling' : 'Start WebGL Profiling'}</MenuItemWithKeybind>
      </MenuBarItem>
    )
  )
})
