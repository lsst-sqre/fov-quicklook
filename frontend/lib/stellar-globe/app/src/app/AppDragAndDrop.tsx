import { ReactNode, useCallback } from "react"
import { DragAndDrop } from "../common/components/DragAndDrop"
import { useAddCatalogFile } from "./features/catalog/useAddCatalogFileList"
import { useAddFitsImageFile } from "./features/fitsImage/useAddFitsImageFile"
import { readJsonFile } from "../common/utils/readJsonFile"
import { useImportRegionJson } from "./features/regions/useImportRegionFile"


type Props = {
  children: ReactNode
}


export function AppDragAndDrop({ children }: Props) {
  const addCatalogFile = useAddCatalogFile()
  const addFitsImageFile = useAddFitsImageFile()
  const handleJsonFile = useHandleJsonFile()
  const onDropFiles = useCallback((fileList: FileList) => {
    for (const file of fileList) {
      const suffix = file.name.toLowerCase().split('.').pop()
      switch (suffix) {
        case 'csv':
          addCatalogFile(file)
          break
        case 'fits':
          addFitsImageFile(file)
          break
        case 'json':
          handleJsonFile(file)
          break
        default:
          alert(`Unsupported file type: ${file.name}: ${file.type}`)
      }
    }
  }, [addCatalogFile, addFitsImageFile, handleJsonFile])

  return (
    <DragAndDrop onFileDrop={onDropFiles}>
      {children}
    </DragAndDrop>
  )
}


function useHandleJsonFile() {
  const importRegionJson = useImportRegionJson()

  return useCallback(async (file: File) => {
    const json = await readJsonFile(file)
    try {
      const { $type, $content } = json
      switch ($type) {
        case useImportRegionJson.$type:
          importRegionJson(json)
          break
      }
    }
    catch (e) {
      alert(e)
    }
  }, [importRegionJson])
}
