import { MenuDivider, MenuItem, SubMenu } from "@szhsin/react-menu"
import { memo, useCallback } from "react"
import { Icon } from "../../../common/components/Icon"
import { MenuBarItem } from "../../../common/components/Menu/MenuBarItem"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { commonSlice } from "./commonSlice"

export const CommonMenu = memo(() => {
  const angleUnit = useAppSelector(state => state.common.angleUnit)
  const dispatch = useAppDispatch()

  const reload = useCallback(() => {
    window.location.hash = ''
    window.location.reload()
  }, [])

  const magFilter = useAppSelector(state => state.common.magFilter)

  return (
    <MenuBarItem label={<Icon type="settings" />}>
      <SubMenu label="Angle Unit">
        <MenuItem type="checkbox" checked={angleUnit === 'sexadecimal'} onClick={() => dispatch(commonSlice.actions.unitChanged({ angleUnit: 'sexadecimal' }))}>Sexadecimal</MenuItem>
        <MenuItem type="checkbox" checked={angleUnit === 'degree'} onClick={() => dispatch(commonSlice.actions.unitChanged({ angleUnit: 'degree' }))}>Degree</MenuItem>
        <MenuItem type="checkbox" checked={angleUnit === 'radian'} onClick={() => dispatch(commonSlice.actions.unitChanged({ angleUnit: 'radian' }))}>Radian</MenuItem>
      </SubMenu>
      <SubMenu label="Mag Filter">
        <MenuItem type="checkbox" checked={magFilter === 'linear'} onClick={() => dispatch(commonSlice.actions.magFilterChanged({ magFilter: 'linear' }))}>Linear</MenuItem>
        <MenuItem type="checkbox" checked={magFilter === 'nearest'} onClick={() => dispatch(commonSlice.actions.magFilterChanged({ magFilter: 'nearest' }))}>Nearest</MenuItem>
      </SubMenu>
      <MenuDivider />
      <MenuItem onClick={reload}>Reload</MenuItem>
    </MenuBarItem>
  )
})

setDisplayName({ CommonMenu })