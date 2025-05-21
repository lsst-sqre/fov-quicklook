import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { Fragment, useCallback, useRef } from "react"
import { MaterialSymbol } from "../../../../components/MaterialSymbol"
import { CcdMeta, useGetVisitMetadataQuery } from "../../../../store/api/openapi"
import { CopyTemplate } from "../../../../store/features/copyTemplateSlice"
import { useAppSelector } from "../../../../store/hooks"
import { copyTextToClipboard } from "../../../../utils/copyTextToClipboard"
import { download } from "../../../../utils/download"
import { useFocusedCcd } from "../../hooks"
import { ContextMenuWithClickedCoord } from "./ContextMenuWithClickedCoord"
import { interpoateText } from "./interpoateText"
import { env } from "../../../../env"


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
      const fitsUrl = `${env.baseUrl}/api/quicklooks/${id}/fits/${ccdMeta.ccd_id.ccd_name}`
      download(fitsUrl, `${id}-${ccdMeta.ccd_id.ccd_name}.fits`)
    }
  }, [ccdMeta])

  return (
    <Fragment>
      {ccdMeta &&
        <TemplateMenus ccdMeta={ccdMeta} />
      }
      <MenuDivider />
      <MenuItem disabled={!ccdMeta} onClick={copyId}>
        <MenuIcon symbol="content_copy" />
        Copy ID to Clipboard
      </MenuItem>
      <MenuItem disabled={!ccdMeta} onClick={openHeaerPage}>
        <MenuIcon symbol="open_in_new" />
        Show FITS Header
      </MenuItem> <MenuDivider />
      <MenuItem disabled={!ccdMeta} onClick={downloadThisFitsFile}>
        <MenuIcon symbol="download" />
        Download this FITS File
      </MenuItem>
    </Fragment>
  )
}


function MenuIcon({ symbol }: { symbol: Parameters<typeof MaterialSymbol>[0]['symbol'] }) {
  return (
    <div style={{ width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '1em' }}>
      <MaterialSymbol symbol={symbol} />
    </div>
  )
}


function TemplateMenus({ ccdMeta }: { ccdMeta: CcdMeta }) {
  const templates = useAppSelector(state => state.copyTemplate.templates)

  return (
    <>
      {templates.map((t) => <TemplateMenu key={t.name} template={t} ccdMeta={ccdMeta} />)}
    </>
  )
}


function TemplateMenu({ template, ccdMeta }: { template: CopyTemplate, ccdMeta: CcdMeta }) {
  const { data: metadata } = useGetVisitMetadataQuery({ id: ccdMeta.ccd_id.visit.id, ccdName: ccdMeta.ccd_id.ccd_name })

  const handleClick = useCallback(async () => {
    if (metadata) {
      const text = interpoateText(template.template, metadata)
      if (template.isUrl) {
        window.open(text)
      } else {
        await copyTextToClipboard(text)
      }
    }
  }, [metadata, template])

  return (
    <MenuItem
      title={ccdMeta.ccd_id.visit.id}
      onClick={handleClick}
      disabled={!metadata}
    >
      <MenuIcon symbol={template.isUrl ? "open_in_new" : "content_copy"} />
      {template.name}
    </MenuItem>
  )
}
