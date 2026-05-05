import { MenuHeader, MenuItem } from "@szhsin/react-menu"
import { Fragment, memo } from "react"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { MenuItemWithKeybind } from "../../keybindings/MenuItemWithKeybind"

export const SesameMenu = memo(() => {
  return (
    <Fragment>
      <MenuHeader>Sesame</MenuHeader>
      <MenuItemWithKeybind keybind="inputSesameQuery" >Find Object by Sesame</MenuItemWithKeybind>
      <MenuItem
        href="https://cds.unistra.fr/cgi-bin/Sesame"
        target="_blank"
        rel="noreferrer"
      >
        Sesame Name Resolver @ CDS
      </MenuItem>
    </Fragment>
  )
})

setDisplayName({ SesameMenu })

