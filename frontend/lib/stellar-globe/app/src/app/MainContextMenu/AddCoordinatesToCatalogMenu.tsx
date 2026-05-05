import { nanoid } from "@reduxjs/toolkit"
import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem, SubMenu } from "@szhsin/react-menu"
import { useAsyncPrompt } from "../../common/components/Modal/useAsyncPrompt"
import { catalogsSlice } from "../features/catalog/catalogSlice"
import { useAppDispatch, useAppSelector } from "../store/hooks"

export function AddCoordinatesToCatalogMenu({ openedAt }: { openedAt: SkyCoord }) {
  const catalogs = useAppSelector(state => state.catalogs.catalogs)

  const addRowToNewCatalog = useAddRowToNewCatalog()
  const addToExistingCatalog = useAddToExistingCatalog()

  return (
    <SubMenu label='Add This Point to'>
      <MenuItem onClick={() => addRowToNewCatalog(openedAt)}>New Catalog</MenuItem>
      <MenuDivider />
      {catalogs.map(catalog => (
        <MenuItem key={catalog.id} onClick={() => addToExistingCatalog(openedAt, catalog.id)}>
          {catalog.name}
        </MenuItem>
      ))}
    </SubMenu>
  )
}


function useAddRowToNewCatalog() {
  const asyncPrompt = useAsyncPrompt()
  const dispatch = useAppDispatch()

  const addRowToNewCatalog = async (openedAt: SkyCoord) => {
    // TODO: move to catalogsSlice
    const name = await asyncPrompt('New Catalog Name ?')
    if (name) {
      const ra = openedAt.a.deg
      const dec = openedAt.d.deg
      const id = nanoid()
      dispatch(catalogsSlice.actions.catalogAdded({
        id,
        name,
        attributes: [],
        fields: ['Ra', 'Dec', 'Note'],
        markers: [],
      }))
      dispatch(catalogsSlice.actions.rowAdded({
        id,
        marker: { position: openedAt.xyz },
        attributes: [ra.toString(), dec.toString(), ''],
        insertAt: 0,
      }))
    }
  }
  return addRowToNewCatalog
}


function useAddToExistingCatalog() {
  const catalogs = useAppSelector(state => state.catalogs.catalogs)
  const dispatch = useAppDispatch()

  const addToExistingCatalog = (openedAt: SkyCoord, catalogId: string) => {
    // TODO: move to catalogsSlice
    const catalog = catalogs.find(catalog => catalog.id === catalogId)!
    const fields = catalog.fields.slice() // copy because catalog.fields is immutable
    let [raColumn, decColumn]: [number, number] = findCoordColumns(fields)

    if (raColumn < 0) {
      dispatch(catalogsSlice.actions.fieldAdded({ id: catalogId, field: 'Ra', insertAt: fields.length }))
      fields.push('Ra')
      raColumn = fields.length
    }
    if (decColumn < 0) {
      dispatch(catalogsSlice.actions.fieldAdded({ id: catalogId, field: 'Dec', insertAt: fields.length }))
      fields.push('Dec')
      decColumn = fields.length
    }

    const ra = openedAt.a.deg
    const dec = openedAt.d.deg
    const attribute: string[] = new Array(fields.length).fill('')
    attribute[raColumn] = ra.toString()
    attribute[decColumn] = dec.toString()

    dispatch(catalogsSlice.actions.rowAdded({
      id: catalogId,
      marker: { position: openedAt.xyz },
      attributes: attribute,
      insertAt: catalog.markers.length,
    }))

    dispatch(catalogsSlice.actions.dialogToggled({ id: catalogId, opened: true }))
  }

  return addToExistingCatalog
}


function findCoordColumns(fields: string[]): [number, number] {
  // Find the column numbers of Ra and Dec from fields
  // However, Ra and Dec column names have various variations, so we support them.
  const raCandidates = ['ra', 'ra2000']
  const decCandidates = ['dec', 'dec2000']

  let raColumn = -1
  let decColumn = -1
  for (let i = 0; i < fields.length; i++) {
    const field = fields[i].toLowerCase()
    if (raCandidates.includes(field)) {
      raColumn = i
    }
    if (decCandidates.includes(field)) {
      decColumn = i
    }
  }
  return [raColumn, decColumn]
}
