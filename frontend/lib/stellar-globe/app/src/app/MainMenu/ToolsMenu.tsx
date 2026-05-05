import { MenuDivider, MenuHeader, MenuItem } from "@szhsin/react-menu"
import { MaterialSymbol } from "material-symbols"
import { Icon } from "../../common/components/Icon"
import { MenuBarItem } from "../../common/components/Menu/MenuBarItem"
import { RegionsMenu } from "../features/regions/RegionsMenu"
import { regionsSlice } from "../features/regions/regionsSlice"
import { MenuItemWithKeybind } from "../keybindings/MenuItemWithKeybind"
import { useAppDispatch, useAppSelector } from "../store/hooks"


type ToolType = ReturnType<typeof regionsSlice['getInitialState']>['tool']


const toolDefs: { [K in ToolType]: {
  icon: MaterialSymbol
  displayName: string
}
} = {
  pan: {
    icon: '360',
    // icon: 'open_with',
    displayName: 'Pan',
  },
  circle: {
    icon: 'circle',
    displayName: 'Circular Region',
  },
  line: {
    icon: 'straighten',
    displayName: 'Linear Region',
  },
  rect: {
    icon: 'crop_square',
    displayName: 'Rectangular Region',
  },
  text: {
    icon: 'title',
    displayName: 'Text',
  },
  path: {
    icon: 'pentagon',
    displayName: 'Polygon',
  },
} as const


export function ToolsMenu() {
  const selectedTool = useAppSelector(state => state.regions.tool)
  const toolPinned = useAppSelector(state => state.regions.toolPinned)
  const dispatch = useAppDispatch()

  const typeToKeybidn = {
    'line': 'toggleLineTool',
    'circle': 'toggleCircleTool',
    'rect': 'toggleRectTool',
    'pan': undefined,
    'text': 'toggleTextTool',
  } as const

  return (
    <MenuBarItem
      label={<Icon type={toolDefs[selectedTool].icon} />}
    >
      {(['pan', 'line', 'circle', 'rect', 'text'] as const).map(tool => (
        <MenuItemWithKeybind
          key={tool}
          type='checkbox'
          checked={tool === selectedTool}
          keybind={typeToKeybidn[tool]}
        >
          <Icon type={toolDefs[tool].icon} marginRight />
          {toolDefs[tool].displayName}
        </MenuItemWithKeybind>
      ))}
      <MenuDivider />
      <MenuItem type="checkbox" checked={toolPinned} onClick={() => dispatch(regionsSlice.actions.toolPinnedToggled())}>Pin Tool</MenuItem>
      <MenuDivider />
      <MenuHeader>Regions</MenuHeader>
      <RegionsMenu />
    </MenuBarItem>
  )
}
