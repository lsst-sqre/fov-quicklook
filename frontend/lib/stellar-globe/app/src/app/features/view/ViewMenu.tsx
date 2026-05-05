import { MenuDivider, MenuItem, SubMenu } from '@szhsin/react-menu'
import { Icon } from '../../../common/components/Icon'
import { MenuBarItem } from '../../../common/components/Menu/MenuBarItem'
import { useFullscreen } from '../../../common/hooks/useFullscreen'
import { useAppContext } from '../../context'
import { MenuItemWithKeybind } from "../../keybindings/MenuItemWithKeybind"
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { AppearanceLayersMenu } from '../appearanceLayers/AppearanceLayerMenu'
import { cameraSlice } from '../camera/cameraSlice'
import { SesameMenu } from '../sesame/SesameMenu'


export function ViewMenu() {
  const { rootElementRef } = useAppContext()
  const { isFullscreen } = useFullscreen(rootElementRef)
  const camera = useAppSelector(state => state.camera)
  const dispatch = useAppDispatch()

  return (
    <MenuBarItem label={<Icon type="visibility" />}>
      <SubMenu label='Layers'>
        <AppearanceLayersMenu />
      </SubMenu>
      <SubMenu label="Projection">
        <MenuItem type='checkbox' checked={camera.projection === 'GNOMONIC'} onClick={_ => dispatch(cameraSlice.actions.projectionUpdated('GNOMONIC'))} >Gnomonic</MenuItem>
        <MenuItem type='checkbox' checked={camera.projection === 'STEREOGRAPHIC'} onClick={_ => dispatch(cameraSlice.actions.projectionUpdated('STEREOGRAPHIC'))} >Stereographic</MenuItem>
        <MenuItem type='checkbox' checked={camera.projection === 'FLOATING_EYE'} onClick={_ => dispatch(cameraSlice.actions.projectionUpdated('FLOATING_EYE'))} >Stellar Globe</MenuItem>
        <MenuDivider />
        <MenuItemWithKeybind keybind='toggleProjection'>Toggle</MenuItemWithKeybind>
      </SubMenu>
      <MenuDivider />
      <MenuItemWithKeybind type='checkbox' checked={camera.retina} keybind='toggleRetina' >Retina</MenuItemWithKeybind>
      <MenuItemWithKeybind type='checkbox' checked={isFullscreen} disabled={!document.fullscreenEnabled} keybind='toggleFullscreen'>Fullscreen</MenuItemWithKeybind>
      <MenuDivider />
      <SubMenu label="Zoom">
        <MenuItemWithKeybind keybind='zoom2arcmin'>2&prime;</MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='zoom20arcmin'>20&prime;</MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='zoom1deg'>1&deg;</MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='zoom2deg'>2&deg;</MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='zoom10deg'>10&deg;</MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='zoomArctan2'>tan(&theta;)=2</MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='zoomHscScale'>1:1 Pixel Mapping (HSC)</MenuItemWithKeybind>
        <MenuDivider />
        <MenuItemWithKeybind keybind='northUp'>
          <Icon type="north" marginRight />
          North Up
        </MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='rotate90'>
          <Icon type="rotate_left" marginRight />
          Rotate 90&deg;
        </MenuItemWithKeybind>
        <MenuItemWithKeybind keybind='rotate270'>
          <Icon type="rotate_right" marginRight />
          Rotate -90&deg;
        </MenuItemWithKeybind>
      </SubMenu>
      <MenuItemWithKeybind keybind='moveToCoords'>Move to Specified Coordinates</MenuItemWithKeybind>
      <MenuDivider />
      <SesameMenu />
    </MenuBarItem>
  )
}
