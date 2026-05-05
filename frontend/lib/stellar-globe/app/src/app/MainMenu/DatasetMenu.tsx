import { MenuDivider, MenuHeader, MenuItem } from '@szhsin/react-menu'
import { MenuBarItem } from '../../common/components/Menu/MenuBarItem'
import { tractTileLayersSlice } from '../features/tractTileLayers/tractTileLayersSlice'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { Icon } from '../../common/components/Icon'
import { HipsMenu } from '../features/hipsLayers/hipsMenu'
import { useCallback } from 'react'


export function DatasetMenu() {
  const layers = useAppSelector(state => state.tractTileLayers.layers)
  const dispatch = useAppDispatch()

  const addTileLayer = useCallback(() => {
    const baseUrl = prompt('Enter the URL of the tile layer')
    if (baseUrl) {
      dispatch(tractTileLayersSlice.actions.layerAdded({
        baseUrl,
        name: baseUrl.split('/').filter(s => s.length > 0).pop() ?? baseUrl,
      }))
    }
  }, [dispatch])

  return (
    <MenuBarItem label={<Icon type="folder_open" />}>
      <MenuHeader>hscMap</MenuHeader>
      {layers.map(({ baseUrl, name, visible }) => (
        <MenuItem
          type='checkbox'
          key={baseUrl}
          checked={visible}
          onClick={() => {
            dispatch(tractTileLayersSlice.actions.layerToggled({ name, visible: !visible }))
          }}
        >{name}</MenuItem>
      ))}
      <MenuDivider />
      <MenuItem onClick={addTileLayer}>
        Add Tile Layer...
      </MenuItem>
      <MenuDivider />
      <MenuHeader>HiPS</MenuHeader>
      <HipsMenu />
    </MenuBarItem>
  )
}
