import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { Fragment, useCallback, useRef } from "react"
import { CcdMeta } from "../../../../store/api/openapi"
import { copyTextToClipboard } from "../../../../utils/copyTextToClipboard"
import { download } from "../../../../utils/download"
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

  const openHeaerPage = useCallback(() => {
    if (ccdMeta) {
      const visit = ccdMeta.ccd_id.visit
      const visitId = `${visit.id}`
      window.open(`#/header/${visitId}/${ccdMeta.ccd_id.ccd_name}`)
    }
  }, [ccdMeta])

  const downloadThisFitsFile = useCallback(() => {
    if (ccdMeta) {
      const { id } = ccdMeta.ccd_id.visit
      const fitsUrl = `./api/quicklooks/${id}/fits/${ccdMeta.ccd_id.ccd_name}`
      download(fitsUrl, `${id}-${ccdMeta.ccd_id.ccd_name}.fits`)
    }
  }, [ccdMeta])

  return (
    <Fragment>
      {ccdMeta &&
        <MenuItem disabled>{ccdMeta.ccd_id.ccd_name}</MenuItem>
      }
      <MenuDivider />
      <MenuItem disabled={!ccdMeta} onClick={copyId}>Copy ID to Clipboard</MenuItem>
      <MenuItem disabled={!ccdMeta} onClick={openHeaerPage}>Show FITS Header</MenuItem>
      <MenuDivider />
      <MenuItem disabled={!ccdMeta} onClick={downloadThisFitsFile}>Download this FITS File</MenuItem>
      {/* <MenuItem disabled={!ccdMeta} onClick={showHeader}>Show Headers</MenuItem> */}
      {/* <MenuItem onClick={donwload}>Download Raw FITS</MenuItem> */}
    </Fragment>
  )
}
