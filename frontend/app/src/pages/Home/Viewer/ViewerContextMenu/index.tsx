import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { Fragment, useCallback, useRef } from "react"
import { CcdMeta, DataSourceCcdMetadata, api, useGetVisitMetadataQuery } from "../../../../store/api/openapi"
import { copyTextToClipboard } from "../../../../utils/copyTextToClipboard"
import { download } from "../../../../utils/download"
import { useFocusedCcd } from "../../hooks"
import { ContextMenuWithClickedCoord } from "./ContextMenuWithClickedCoord"
import { useAppSelector } from "../../../../store/hooks"
import { CopyTemplate } from "../../../../store/features/copyTemplateSlice"


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
        <CopyMenus ccdMeta={ccdMeta} />
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


function CopyMenus({ ccdMeta }: { ccdMeta: CcdMeta }) {
  const templates = useAppSelector(state => state.copyTemplate.templates)

  return (
    <>
      {templates.map((t) => <CopyTemplateMenuItem key={t.name} template={t} ccdMeta={ccdMeta} />)}
    </>
  )
}


function CopyTemplateMenuItem({ template, ccdMeta }: { template: CopyTemplate, ccdMeta: CcdMeta }) {
  const { data: metadata } = useGetVisitMetadataQuery({ id: ccdMeta.ccd_id.visit.id, ccdName: ccdMeta.ccd_id.ccd_name })

  const runCopyTemplate = useCallback(async () => {
    if (metadata) {
      const text = interpoateText(template.template, metadata)
      await copyTextToClipboard(text)
    }
  }, [metadata, template.template])

  return (
    <MenuItem
      title={ccdMeta.ccd_id.visit.id}
      onClick={runCopyTemplate}
      disabled={!metadata}
    >
      {template.name}
    </MenuItem>
  )
}


function interpoateText(template: string, meta: DataSourceCcdMetadata): string {
  // metaには↓が含まれる
  //
  // visit: Visit;
  // ccd_name: string;
  // ccd_id: number;
  // exposure: number;
  // day_obs: number;

  // この関数は、templateの中に%(visit)や%(ccd_id)が含まれている場合、それをmetaの値に置き換える

  type Meta2 = DataSourceCcdMetadata & {
    dataType: string
  }

  const meta2 = { ...meta } as Meta2
  meta2.dataType = meta.visit.id.split(':')[0]

  return template.replace(/%\((\w+)\)/g, (_, key) => {
    if (key in meta2) {
      return `${meta2[key as keyof Meta2]}`
    }
    return _
  })
}
