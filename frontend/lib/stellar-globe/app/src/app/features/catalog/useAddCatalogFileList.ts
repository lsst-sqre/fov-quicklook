import { Globe, SkyCoord, angle } from "@stellar-globe/stellar-globe"
import { useCallback } from "react"
import { useAppContext, useAppGetState } from "../../context"
import { useAppDispatch } from "../../store/hooks"
import { Catalog, catalogsSlice, parseCatalogCsvText } from "./catalogSlice"


export function useAddCatalogFile() {
  const dispatch = useAppDispatch()
  const getState = useAppGetState()
  const { globeHandle } = useAppContext()

  return useCallback((file: File) => {
    if (file.type === 'text/csv') {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target?.result as string
        let parsedResults: ReturnType<typeof parseCatalogCsvText>
        try {
          parsedResults = parseCatalogCsvText(text)
        }
        catch (error) {
          alert(error)
          return
        }
        dispatch(catalogsSlice.actions.catalogAdded({ name: file.name, ...parsedResults }))
        goToCatalog(getState().catalogs.catalogs.slice(-1)[0], globeHandle.current!())
      }
      reader.readAsText(file)
    }
    else {
      alert(`Unsupported file type: ${file.name}: ${file.type}`)
    }
  }, [dispatch, getState, globeHandle])
}


function goToCatalog(catalog: Catalog, globe: Globe) {
  if (catalog.markers.length > 0) {
    const coord = SkyCoord.fromXyz(catalog.markers[0].position)
    globe.camera.jumpTo({ fovy: angle.deg2rad(1) }, { coord })
  }
}


export function useGoToCatalog() {
  const { globeHandle } = useAppContext()
  return useCallback((catalog: Catalog) => {
    goToCatalog(catalog, globeHandle.current!())
  }, [globeHandle])
}
