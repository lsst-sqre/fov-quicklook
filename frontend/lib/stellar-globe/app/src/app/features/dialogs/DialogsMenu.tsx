import { MenuDivider, MenuItem, SubMenu } from "@szhsin/react-menu"
import { memo } from "react"
import { Icon } from "../../../common/components/Icon"
import { MenuBarItem } from "../../../common/components/Menu/MenuBarItem"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { MenuItemWithKeybind } from "../../keybindings/MenuItemWithKeybind"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { commonSlice } from "../common/commonSlice"
import { useAppContext } from "../../context"
import { catalogsSlice } from "../catalog/catalogSlice"
import { fitsImageSlice } from "../fitsImage/fitsImageSlice"

export const DialogsMenu = memo(() => {
  const tone = useAppSelector(state => state.tractTileLayers.toneDialogVisible)
  const regions = useAppSelector(state => state.regions.regionsDialogVisible)
  const hips = useAppSelector(state => state.hipsLayers.hipsDialogVisible)
  const catalogsDialog = useAppSelector(state => state.catalogs.catalogsDialogVisible)
  const localFitsImageDialog = useAppSelector(state => state.fitsImage.dialogVisible)
  const currentPositionHint = useAppSelector(state => state.common.dialogPositionHint)
  const dispatch = useAppDispatch()
  const { dialogContext } = useAppContext()
  const catalogs = useAppSelector(state => state.catalogs.catalogs)

  const positionMenu = (label: string, positionHint: PositionHint) => {
    return (
      <MenuItem
        type="checkbox"
        onClick={() => {
          dispatch(commonSlice.actions.dialogPositionHintChanged(positionHint))
          dialogContext.current?.rearrange()
        }}
        checked={positionHintName(currentPositionHint) === positionHintName(positionHint)}
      >
        {label}
      </MenuItem>
    )
  }

  return (
    <MenuBarItem label={<Icon type='select_window' />} >
      <MenuItemWithKeybind type='checkbox' checked={tone} keybind="toggleToneDialog"><Icon type='tune' marginRight />Tone</MenuItemWithKeybind>
      <MenuItemWithKeybind type='checkbox' checked={regions} keybind="toggleRegionsDialog"><Icon type='architecture' marginRight />Regions</MenuItemWithKeybind>
      <MenuItemWithKeybind type='checkbox' checked={hips} keybind="toggleHipsDialog"><Icon type='layers' marginRight />HiPS</MenuItemWithKeybind>
      <MenuItemWithKeybind type='checkbox' checked={catalogsDialog} keybind="toggleCatalogsDialog"><Icon type='table' marginRight />Catalogs</MenuItemWithKeybind>
      <MenuItem type='checkbox' checked={localFitsImageDialog} onClick={() => dispatch(fitsImageSlice.actions.dialogToggled())}><Icon type='photo_library' marginRight />FITS Images</MenuItem>
      <MenuDivider />
      <SubMenu label="Catalogs">
        {
          catalogs.map(c => (
            <MenuItem
              key={c.id} type='checkbox' checked={c.dialog.opened}
              onClick={() => dispatch(catalogsSlice.actions.dialogToggled({ id: c.id }))}
            >{c.name}</MenuItem>
          ))
        }
      </SubMenu>
      <MenuDivider />
      <MenuItemWithKeybind keybind="rearrangeDialogs" ><Icon marginRight type='grid_view' />Rearrange</MenuItemWithKeybind>
      <MenuItemWithKeybind keybind="closeAllDialogs" ><Icon marginRight type='close' />Close All</MenuItemWithKeybind>
      <MenuDivider />
      <SubMenu label="Default Position">
        {positionMenu('Top Left', { top: 8, left: 8 })}
        {positionMenu('Top Right', { top: 8, right: 8 })}
        {positionMenu('Bottom Left', { bottom: 8, left: 8 })}
        {positionMenu('Bottom Right', { bottom: 8, right: 8 })}
      </SubMenu>
    </MenuBarItem>
  )
})
setDisplayName({ DialogsMenu })


type PositionHint = Parameters<typeof commonSlice.actions.dialogPositionHintChanged>[0]


// const positionPresets = {
//   topleft: {
//     top: 8, left: 8,
//   },
//   topright: {
//     top: 8, right: 8,
//   },
//   bottomleft: {
//     bottom: 8, left: 8,
//   },
//   bottomright: {
//     bottom: 8, right: 8,
//   },
// }


function positionHintName(hint: PositionHint) {
  const { bottom, left, right, top } = hint
  return JSON.stringify([top, bottom, left, right])
}
