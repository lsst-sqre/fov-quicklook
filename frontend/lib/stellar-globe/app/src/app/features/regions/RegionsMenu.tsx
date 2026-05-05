import { MenuDivider, MenuItem } from "@szhsin/react-menu"
import { Fragment, useCallback, useMemo } from "react"
import { askLocalFileList } from "../../../common/utils/askLocalFileList"
import { downloadJson } from "../../../common/utils/downloadFile"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { regionsSlice } from "./regionsSlice"
import { useImportRegionJson } from "./useImportRegionFile"
import { readJsonFile } from "../../../common/utils/readJsonFile"


export function RegionsMenu() {
  const autoColor = useAppSelector(state => state.regions.autoColor)
  const dispatch = useAppDispatch()
  const regions = useAppSelector(state => state.regions.regions)
  const clearRegionsDisabled = useMemo(() => regions.length === 0, [regions.length])
  const exportRegions = useExportRegions()
  const importRegions = useImportRegions()

  return (
    <Fragment>
      <MenuItem type="checkbox" checked={autoColor} onClick={() => dispatch(regionsSlice.actions.autoColorToggled())}>Auto Color</MenuItem>
      <MenuItem
        disabled={clearRegionsDisabled}
        onClick={() => dispatch(regionsSlice.actions.regionsCleared({}))}
      >Clear All Regions</MenuItem>
      <MenuDivider />
      <MenuItem onClick={exportRegions}>Export Regions</MenuItem>
      <MenuItem onClick={importRegions}>Import Regions</MenuItem>
    </Fragment>
  )
}


function useExportRegions() {
  const regions = useAppSelector(state => state.regions.regions)
  const exportRegions = useCallback(() => {
    const filename = prompt('Filename?', 'regions.json')
    if (filename) {
      downloadJson({ content: { $type: useImportRegionJson.$type, $content: regions }, filename })
    }
  }, [regions])
  return exportRegions
}


function useImportRegions() {
  const importRegionFile = useImportRegionJson()

  const uploadRegions = useCallback(async () => {
    const files = await askLocalFileList({ multiple: true })
    for (const file of files) {
      if (file.type === 'application/json') {
        try {
          importRegionFile(await readJsonFile(file))
        }
        catch (e) {
          alert(e)
        }
      }
      else {
        alert(`Unsupported file type: ${file.type} -> ${file.type}`)
      }
    }
  }, [importRegionFile])
  return uploadRegions
}
