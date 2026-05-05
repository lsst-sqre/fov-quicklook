import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { memo } from "react"
import { Icon } from "../../../common/components/Icon"
import { MenuBarItem } from "../../../common/components/Menu/MenuBarItem"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { useStateHistory } from "../../store/StateHistoryProvider"
import { appStateHistoryActions, useAppDispatch } from "../../store/hooks"
import { MenuItemWithKeybind } from "../../keybindings/MenuItemWithKeybind"

export const HistoryMenu = memo(() => {
  const history = useStateHistory()
  const dispatch = useAppDispatch()

  return (
    <MenuBarItem label={<Icon type="history" />}>
      <MenuItemWithKeybind
        disabled={history.currentIndex + 1 >= history.records.length}
        keybind="historyUndo"
      >
        Undo
      </MenuItemWithKeybind>
      <MenuItemWithKeybind
        disabled={history.currentIndex < 1}
        keybind="historyRedo"
      >
        Redo
      </MenuItemWithKeybind>
      {
        history.records.length > 0 &&
        <MenuDivider />
      }
      {history.records.map((r, index) => (
        <MenuItem
          type='checkbox'
          key={r.id}
          onClick={() => dispatch(appStateHistoryActions.timeTravel({ index }))}
          checked={index === history.currentIndex}
        >
          {r.summary ?? r.type}
        </MenuItem>
      ))}
    </MenuBarItem>
  )
})

setDisplayName({ HistoryMenu })
