import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { Fragment, useCallback, useMemo, useRef } from "react"
import { MaterialSymbol } from "../../../../components/MaterialSymbol"
import { env } from "../../../../env"
import { CcdMetadata, useGetVisitMetadataQuery } from "../../../../store/api/openapi"
import { CopyTemplate } from "../../../../store/features/copyTemplateSlice"
import { homeSlice } from "../../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../../store/hooks"
import { copyTextToClipboard } from "../../../../utils/copyTextToClipboard"
import { download } from "../../../../utils/download"
import { useFocusedCcd } from "../../hooks"
import { ContextMenuWithClickedCoord } from "./ContextMenuWithClickedCoord"
import { interpoateText } from "./interpoateText"


export function ViewerContextMenu() {
  const focusedCcd = useFocusedCcd()
  const CcdMetadataAtOpen = useRef<CcdMetadata>()

  return (
    <ContextMenuWithClickedCoord
      render={openedAt => <ContextMenuAtPosition openedAt={openedAt} CcdMetadata={CcdMetadataAtOpen.current} />}
      onOpen={() => CcdMetadataAtOpen.current = focusedCcd}
    />
  )
}

function useVisit() {
  const currentId = useAppSelector(state => state.home.currentQuicklook)
  if (currentId === undefined) {
    throw new Error("No current quicklook")
  }
  return currentId
}



function ContextMenuAtPosition({ CcdMetadata }: { openedAt: SkyCoord, CcdMetadata: CcdMetadata | undefined }) {
  const dispatch = useAppDispatch()
  const visit = useVisit()

  const openHeaderPage = useCallback(() => {
    if (CcdMetadata) {
      window.open(`${env.baseUrl}/header/${visit}/${CcdMetadata.ccd_name}`)
    }
  }, [CcdMetadata, visit])

  const downloadThisFitsFile = useCallback(() => {
    if (CcdMetadata) {
      const fitsUrl = `${env.baseUrl}/api/quicklooks/${visit}/fits/${CcdMetadata.ccd_name}`
      download(fitsUrl, `${visit}-${CcdMetadata.ccd_name}.fits`)
    }
  }, [CcdMetadata, visit])

  const toggleHighlight = useCallback(() => {
    if (CcdMetadata) {
      dispatch(homeSlice.actions.toggleHighlightCcd(CcdMetadata.ccd_name))
    }
  }, [CcdMetadata, dispatch])

  return (
    <Fragment>
      {CcdMetadata &&
        <TemplateMenus CcdMetadata={CcdMetadata} />
      }
      <MenuDivider />
      <MenuItem disabled={!CcdMetadata} onClick={toggleHighlight}>
        <MenuIcon symbol="star" />
        Toggle Highlight
      </MenuItem>
      <MenuItem disabled={!CcdMetadata} onClick={openHeaderPage}>
        <MenuIcon symbol="open_in_new" />
        Show FITS Header
      </MenuItem>
      <MenuDivider />
      <MenuItem disabled={!CcdMetadata} onClick={downloadThisFitsFile}>
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


function TemplateMenus({ CcdMetadata }: { CcdMetadata: CcdMetadata }) {
  const templates = useAppSelector(state => state.copyTemplate.templates)

  return (
    <>
      {templates.map((t) => <TemplateMenu key={t.name} template={t} CcdMetadata={CcdMetadata} />)}
    </>
  )
}


function TemplateMenu({ template, CcdMetadata }: { template: CopyTemplate, CcdMetadata: CcdMetadata }) {
  const visit = useVisit()
  const { data: metadata } = useGetVisitMetadataQuery({ visitName: visit, ccdName: CcdMetadata.ccd_name })

  const text = useMemo(() => {
    if (!metadata) return 'Loading...'
    return interpoateText(template.template, metadata)
  }, [metadata, template.template])

  const handleClick = useCallback(async () => {
    if (metadata) {
      if (template.is_url) {
        window.open(text)
      } else {
        await copyTextToClipboard(text)
      }
    }
  }, [metadata, template, text])

  return (
    <MenuItem
      title={text}
      onClick={handleClick}
      disabled={!metadata}
    >
      <MenuIcon symbol={template.is_url ? "open_in_new" : "content_copy"} />
      {template.name}
    </MenuItem>
  )
}
