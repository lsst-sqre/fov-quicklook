import Papa from 'papaparse'

import { MarkerType, markerTypes } from '@stellar-globe/stellar-globe'
import { MenuDivider, MenuItem, SubMenu } from '@szhsin/react-menu'
import { Fragment, memo, useCallback, useId } from "react"
import { ColorPickerRgba } from "../../../common/components/ColorPicker"
import EditableDiv from '../../../common/components/EditableDiv'
import { Icon } from "../../../common/components/Icon"
import { RegularMenu } from '../../../common/components/Menu/RegularMenu'
import { askLocalFileList } from '../../../common/utils/askLocalFileList'
import { downloadFile } from '../../../common/utils/downloadFile'
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { AppDialog } from '../../AppDialog'
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { Catalog, catalogsSlice } from "./catalogSlice"
import { generateCSV } from './generateSampleCsv'
import { useAddCatalogFile, useGoToCatalog } from './useAddCatalogFileList'


export const CatalogsDialog = memo(() => {
  const catalogs = useAppSelector(state => state.catalogs.catalogs)
  const visible = useAppSelector(state => state.catalogs.catalogsDialogVisible)
  const dispatch = useAppDispatch()

  return (
    <AppDialog
      title={<Fragment><Icon type='table' marginRight />Catalogs</Fragment>}
      visible={visible}
      onCloseButtonClick={() => dispatch(catalogsSlice.actions.catalogsDialogToggled({}))}
      menu={<CatalogsMenu />}
    >
      <table>
        <thead>
          <tr>
            {catalogs.length > 0 && (
              <Fragment>
                <th><Icon type='visibility' /></th>
                <th>#</th>
                <th>Name</th>
                <th>Marker</th>
                <th></th>
                <th></th>
              </Fragment>
            )}
          </tr>
        </thead>
        <tbody>
          {catalogs.map(c => <CatalogTr key={c.id} catalog={c} />)}
        </tbody>
      </table>
    </AppDialog>
  )
})


const CatalogTr = memo(({ catalog: c }: { catalog: Catalog }) => {
  const dispatch = useAppDispatch()
  const visibleId = useId()

  return (
    <tr key={c.id}>
      <th>
        <input type='checkbox' checked={c.visible} id={visibleId} onChange={e =>
          dispatch(catalogsSlice.actions.catalogUpdated({ id: c.id, visible: e.currentTarget.checked }))
        } />
      </th>
      <td style={{ textAlign: 'right' }}>
        <label htmlFor={visibleId}>
          {c.attributes.length}
        </label>
      </td>
      <td>
        <EditableDiv
          value={c.name}
          onChange={newName => dispatch(catalogsSlice.actions.catalogUpdated({ id: c.id, name: newName }))} />
      </td>
      <td>
        <select style={{ maxWidth: '8em', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} value={c.defaultType} onChange={e =>
          dispatch(catalogsSlice.actions.catalogUpdated({ id: c.id, defaultType: e.currentTarget.value as MarkerType }))
        }>
          {markerTypes.map(t => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </td>
      <td>
        <ColorPickerRgba color={c.baseColor} onChange={color =>
          dispatch(catalogsSlice.actions.catalogUpdated({ id: c.id, baseColor: color }))
        } />
      </td>
      <td>
        <CatalogMenu catalog={c} />
        <button onClick={() => dispatch(catalogsSlice.actions.catalogDeleted({ id: c.id }))} >
          <Icon type='delete' />
        </button>
      </td>
    </tr>
  )
})
setDisplayName({ CatalogTr })


const CatalogMenu = memo(({ catalog }: { catalog: Catalog }) => {
  const goToCatalog = useGoToCatalog()
  const dispatch = useAppDispatch()
  const catalogs = useAppSelector(state => state.catalogs.catalogs)
  const download = useCallback((options: { onlySelected: boolean }) => {
    const attributes = (options.onlySelected ?
      (Object.keys(catalog.selectedRecords) as any as number[]).map(i => catalog.attributes[i]) :
      catalog.attributes
    )

    const csv = Papa.unparse({
      fields: catalog.fields,
      data: attributes,
    })

    downloadFile({ content: csv, filename: `${catalog.name.replace(/\.csv$/i, '')}${options.onlySelected ? ' (only selected)' : ''}.csv`, type: 'text/csv' })
  }, [catalog.attributes, catalog.fields, catalog.name, catalog.selectedRecords])

  return (
    <RegularMenu renderMenuButtonContents={() => <Icon type='menu' style={{ fontSize: 'normal' }} />}>
      <MenuItem onClick={() => dispatch(catalogsSlice.actions.dialogToggled({ id: catalog.id }))}>
        <Icon type='table' marginRight />
        {catalog.dialog.opened ? 'Close' : 'Open'} Table
      </MenuItem>
      <MenuDivider />
      <MenuItem onClick={() => dispatch(catalogsSlice.actions.rowsFiltered({ id: catalog.id, selected: false }))}>
        <Icon type='filter_alt' marginRight />
        Delete Selected Rows
      </MenuItem>
      <MenuItem onClick={() => dispatch(catalogsSlice.actions.rowsFiltered({ id: catalog.id, selected: true }))}>
        <Icon type='filter_alt' marginRight />
        Delete Unselected Rows
      </MenuItem>
      <MenuItem onClick={() => dispatch(catalogsSlice.actions.selectionInverted({ id: catalog.id }))}>
        <Icon type='select' marginRight />
        Invert Selection
      </MenuItem>
      <MenuItem onClick={() => dispatch(catalogsSlice.actions.allRowsSelected({ id: catalog.id, selected: false }))}>
        <Icon type='select_all' marginRight />
        Deselect All Rows
      </MenuItem>
      <SubMenu label={<Fragment><Icon type='merge' marginRight />Merge</Fragment>}>
        <SubMenu label="Only Selected Rows to">
          {catalogs.map(c => c.id !== catalog.id && (
            <MenuItem
              key={c.id}
              onClick={() => dispatch(catalogsSlice.actions.catalogMerged({ srcId: catalog.id, dstId: c.id, onlySelected: true, deleteSrc: true }))}
            >
              {c.name}
            </MenuItem>
          ))}
        </SubMenu>
        <SubMenu label="All Rows to">
          {catalogs.map(c => c.id !== catalog.id && (
            <MenuItem
              key={c.id}
              onClick={() => dispatch(catalogsSlice.actions.catalogMerged({ srcId: catalog.id, dstId: c.id, onlySelected: false, deleteSrc: true }))}
            >
              {c.name}
            </MenuItem>
          ))}
        </SubMenu>
      </SubMenu>
      <MenuItem onClick={() => dispatch(catalogsSlice.actions.catalogDuplicated({ id: catalog.id }))}>
        <Icon type='copy_all' marginRight />
        Duplicate
      </MenuItem>
      <MenuDivider />
      <MenuItem onClick={() => goToCatalog(catalog)}><Icon type='location_on' marginRight />Go to first row</MenuItem>
      <MenuDivider />
      <MenuItem onClick={() => download({ onlySelected: false })} ><Icon type='download' marginRight />Download as CSV</MenuItem>
      <MenuItem onClick={() => download({ onlySelected: true })}  ><Icon type='download' marginRight />Download as CSV (Only Selected Rows)</MenuItem>
    </RegularMenu>
  )
})


export const CatalogsMenu = memo(() => {
  const addCatalogFiles = useAddCatalogFile()
  const dispatch = useAppDispatch()

  const upload = async () => {
    try {
      const filelist = await askLocalFileList({ multiple: true })
      for (const file of filelist) {
        addCatalogFiles(file)
      }
    }
    catch {
      // do nothing
    }
  }

  const downloadExampleWithColorColumn = useCallback(() => {
    const csv = generateCSV({
      rows: 1000,
      includeColor: true,
      decRange: { min: -0.5, max: 0.5 },
      raRange: { min: 0, max: 1 },
    })
    downloadFile({
      filename: 'example_with_color_column.csv',
      content: csv,
      type: 'text/csv',
    })
  }, [])

  const downloadExampleWithColorAndMarkerTypeColumn = useCallback(() => {
    const csv = generateCSV({
      rows: 1000,
      includeColor: true,
      includeMarkerType: true,
      decRange: { min: -0.5, max: 0.5 },
      raRange: { min: 1, max: 2 },
    })
    downloadFile({
      filename: 'example_with_color_and_marker_type_column.csv',
      content: csv,
      type: 'text/csv',
    })
  }, [])

  const showAttributes = useAppSelector(state => state.catalogs.showAttributes)
  const toggleShowAttributes = () => dispatch(catalogsSlice.actions.showAttributesToggled({ show: !showAttributes }))

  return (
    <Fragment>
      <MenuItem onClick={toggleShowAttributes} type='checkbox' checked={showAttributes} >
        Object Inspector
      </MenuItem>
      <MenuDivider />
      <MenuItem onClick={upload}>
        Upload
      </MenuItem>
      <MenuDivider />
      <SubMenu label="Example Files">
        <MenuItem onClick={downloadExampleWithColorColumn}>
          With Color Column
        </MenuItem>
        <MenuItem onClick={downloadExampleWithColorAndMarkerTypeColumn}>
          With Color Column and Marker Type Column
        </MenuItem>
      </SubMenu>
    </Fragment>
  )
})
setDisplayName({ CatalogsMenu })
