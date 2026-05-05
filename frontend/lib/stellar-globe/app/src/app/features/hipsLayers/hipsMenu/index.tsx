import { MenuItem, SubMenu } from "@szhsin/react-menu"
import { Fragment, memo } from "react"
import { setDisplayName } from "../../../../common/utils/setDisplayName"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { hipsLayersSlice } from "../hipsLayersSlice"
import { TomoegozenSubmenu } from "../tomoegozen"
import { HipsSearch } from "./HipsSearch"
import { HipsDirectoryMenu } from "./directory"


export const HipsMenu = memo(() => {
  const dispatch = useAppDispatch()
  const currentBaseUrl = useAppSelector(state => state.hipsLayers.baseUrl)

  return (
    <Fragment>
      <HipsSearch />
      <SubMenu label="Recommended">
        <MenuItem
          type='checkbox'
          checked={currentBaseUrl === '//hscmap.mtk.nao.ac.jp/hscMap4/misc/hips/gaia'}
          onClick={() => dispatch(hipsLayersSlice.actions.baseUrlChanged({ baseUrl: '//hscmap.mtk.nao.ac.jp/hscMap4/misc/hips/gaia' }))}>
          GAIA DR2
        </MenuItem>
        <TomoegozenSubmenu />
      </SubMenu>
      <HipsDirectoryMenu />
      <MenuItem onClick={() => dispatch(hipsLayersSlice.actions.baseUrlChanged({ baseUrl: undefined }))}>Clear</MenuItem>
      <MenuItem
        href="https://aladin.cds.unistra.fr/hips/list"
        target="_blank"
        rel="noreferrer"
      >
        HiPS list aggregator @ CDS
      </MenuItem>
    </Fragment>
  )
})
setDisplayName({ HipsMenu })
