import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { Fragment, useCallback, useRef } from "react"
import { CcdMeta } from "../../../../store/api/openapi"
import { copyTextToClipboard } from "../../../../utils/copyTextToClipboard"
import { useFocusedCcd } from "../../hooks"
import { ContextMenuWithClickedCoord } from "./ContextMenuWithClickedCoord"


export function ViewerContextMenu() {
  const focusedCcd = useFocusedCcd()
  const ccdMetaAtOpen = useRef<CcdMeta>()

  return (
    <ContextMenuWithClickedCoord
      render={openedAt => <ContextMenuAtPosition openedAt={openedAt} ccdMeta={ccdMetaAtOpen.current} />}
      onOpen={() => ccdMetaAtOpen.current = focusedCcd}
    />
  )
}


function ContextMenuAtPosition({ ccdMeta }: { openedAt: SkyCoord, ccdMeta: CcdMeta | undefined }) {
  const copyId = useCallback(async () => {
    await copyTextToClipboard(ccdMeta?.ccd_id.ccd_name ?? '-')
  }, [ccdMeta?.ccd_id.ccd_name])

  return (
    <Fragment>
      {ccdMeta &&
        <MenuItem disabled>{ccdMeta.ccd_id.ccd_name}</MenuItem>
      }
      <MenuDivider />
      <MenuItem disabled={!ccdMeta} onClick={copyId}>Copy ID to Clipboard</MenuItem>
      {/* <MenuItem disabled={!ccdMeta} onClick={showHeader}>Show Headers</MenuItem> */}
      {/* <MenuItem onClick={donwload}>Download Raw FITS</MenuItem> */}
    </Fragment>
  )
}
