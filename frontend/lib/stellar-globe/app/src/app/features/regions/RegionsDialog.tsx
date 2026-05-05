import { resizableY } from "@stellar-globe/react-draggable-dialog"
import { V4 } from "@stellar-globe/stellar-globe"
import { MaterialSymbol } from "material-symbols"
import { Fragment, memo, useCallback, useMemo, useState } from "react"
import { ColorPickerRgba } from "../../../common/components/ColorPicker"
import EditableDiv from "../../../common/components/EditableDiv"
import { Icon } from "../../../common/components/Icon"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { AppDialog } from "../../AppDialog"
import { useAppContext } from '../../context'
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { RegionsMenu } from "./RegionsMenu"
import { Region, regionView, regionsSlice } from "./regionsSlice"
import { TriStateCheckBox } from "../../../common/components/TriStateCheckBox"


export const RegionsDialog = memo(() => {
  const visible = useAppSelector(state => state.regions.regionsDialogVisible)
  const regions = useAppSelector(state => state.regions.regions)
  const dispatch = useAppDispatch()
  const groupedRegions = useMemo(() => groupRegions(regions), [regions])

  return (
    <AppDialog
      title={<Fragment><Icon type="architecture" marginRight />Regions</Fragment>}
      visible={visible}
      resizable={resizableY}
      onCloseButtonClick={() => dispatch(regionsSlice.actions.regionsDialogToggled({}))}
      menu={<RegionsMenu />}
    >
      <table >
        <thead>
          <tr>
            <th><Icon type='category' /></th>
            <th><Icon type='summarize' /></th>
            <th><Icon type='visibility' /></th>
            <th><Icon type='label' /></th>
            <th><Icon type='palette' /></th>
            <th />
          </tr>
        </thead>
        <tbody>
          {groupedRegions.map(region => <RegionNodeOrRegionGroupTr key={nodeKey(region)} node={region} depth={0} />)}
        </tbody>
      </table>
    </AppDialog>
  )
})
setDisplayName({ RegionsDialog })


function indent(text: string, depth: number) {
  return <span style={{ paddingLeft: `${depth}em` }}>{text}</span>
}


function baseName(path: string) {
  return path.split('/').slice(-1)[0]
}


const RegionNodeOrRegionGroupTr = memo(({ node, depth }: { node: Node, depth: number }) => {
  if (node.type === 'group') {
    return <RegionGroupTr group={node} depth={depth} />
  }
  return <RegionTr region={node.model} depth={depth} />
})
setDisplayName({ RegionNodeOrRegionGroupTr })


const RegionGroupTr = memo(({ group, depth }: { group: Group, depth: number }) => {
  const [opened, setOpened] = useState(false)
  const dispatch = useAppDispatch()
  const children = childRegions(group)
  return (
    <Fragment>
      <tr>
        <td>
          <button onClick={() => setOpened(!opened)}>
            <Icon type={opened ? 'folder_open' : 'folder'} />
          </button>
        </td>
        <td>
          <EditableDiv
            value={group.name}
            display={name => name && indent(baseName(name), depth)}
            onChange={newName => dispatch(
              regionsSlice.actions.regionsRenameGroup({
                nameStartsWith: `${group.name}/`,
                newName,
              })
            )} />
        </td>
        <td>
          {/* set visibility */}
          <TriStateCheckBox
            value={booleanArrayToTriState(children.map(child => child.visible))}
            onChange={value => {
              dispatch(regionsSlice.actions.regionsBatchUpdated({
                nameStartsWith: `${group.name}/`,
                regionDef: { visible: value }
              }))
            }}
          />
        </td>
        <td>
          {/* set showLabel */}
          <TriStateCheckBox
            value={booleanArrayToTriState(children.map(child => child.showLabel))}
            onChange={value => {
              dispatch(regionsSlice.actions.regionsBatchUpdated({
                nameStartsWith: `${group.name}/`,
                regionDef: { showLabel: value }
              }))
            }}
          />
        </td>
        <td>
          {/* set color */}
          <ColorPickerRgba
            color={children[0].color}
            onChange={color => {
              dispatch(regionsSlice.actions.regionsBatchUpdated({
                nameStartsWith: `${group.name}/`,
                regionDef: { color }
              }))
            }}
          />
        </td>
        <td>
          <div>
            <button disabled ><Icon type="location_on" /></button>
            <button
              onClick={() => dispatch(regionsSlice.actions.regionsBatchDeleted({ nameStartsWith: `${group.name}/` }))}
            ><Icon type="delete" /></button>
          </div>
        </td>
      </tr>
      {opened && group.children.map(child => <RegionNodeOrRegionGroupTr key={nodeKey(child)} node={child} depth={depth + 1} />)}
    </Fragment>
  )
})
setDisplayName({ RegionGroupTr })


function childRegions(group: Group): Region[] {
  return group.children.flatMap(child => child.type === 'entry' ? child.model : childRegions(child))
}


function booleanArrayToTriState(a: boolean[]) {
  const n = a.filter(x => x).length
  return n === 0 ? false : n === a.length ? true : null
}


const RegionTr = memo(({ region, depth }: { region: Region, depth: number }) => {
  const dispatch = useAppDispatch()
  const { type, id, color, visible, showLabel } = region

  const onChangeColor = useCallback((color: V4) => {
    dispatch(regionsSlice.actions.regionUpdated({ id, regionDef: { ...region, color } }))
  }, [dispatch, id, region])

  const { globeHandle } = useAppContext()

  const goToRegion = () => {
    const { center, fov } = regionView(region)
    globeHandle.current!().camera.jumpTo({ fovy: 2 * fov }, { coord: center })
  }

  return (
    <tr>
      <td><Icon type={typeIcon[type]} /></td>
      <td>
        <EditableDiv
          value={region.name}
          display={name => name && indent(baseName(name), depth)}
          onChange={newName => dispatch(regionsSlice.actions.regionUpdated({ id, regionDef: { ...region, name: newName } }))} />
      </td>
      <td>
        <input
          type='checkbox' checked={visible}
          onChange={e => dispatch(regionsSlice.actions.regionUpdated({ id, regionDef: { ...region, visible: e.currentTarget.checked } }))} />
      </td>
      <td>
        <input
          type='checkbox' checked={showLabel}
          onChange={e => dispatch(regionsSlice.actions.regionUpdated({ id, regionDef: { ...region, showLabel: e.currentTarget.checked } }))} />
      </td>
      <td>
        <ColorPickerRgba color={color} onChange={onChangeColor} />
      </td>
      <td>
        <div>
          <button
            onClick={goToRegion}
          ><Icon type="location_on" /></button>
          <button
            onClick={() => dispatch(regionsSlice.actions.regionDeleted({ id }))}
          ><Icon type="delete" /></button>
        </div>
      </td>
    </tr>
  )
})
setDisplayName({ RegionTr })


type RegionType = ReturnType<typeof regionsSlice.getInitialState>['regions'][number]['type']


const typeIcon: { [K in RegionType]: MaterialSymbol } = {
  Linear: 'straighten',
  Circular: 'circle',
  Rectangular: 'rectangle',
  Text: 'title',
  Path: 'pentagon',
} as const


type Group = {
  type: 'group'
  name: string
  children: Node[]
}

type Entry = {
  type: 'entry'
  model: Region
}


type Node = Group | Entry


function nodeKey(node: Node) {
  return node.type === 'group' ? node.name : node.model.id
}


function groupRegions(regions: Region[]): Node[] {
  // region.nameを'/'で区切って階層化する
  const nodes: Node[] = []
  for (const region of regions) {
    const parts = region.name.split('/')
    let parent = nodes
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts.slice(0, i + 1).join('/')
      let group = parent.find(node => node.type === 'group' && node.name === part) as Group | undefined
      if (!group) {
        group = { type: 'group', name: part, children: [] }
        parent.push(group)
      }
      parent = group.children
    }
    parent.push({ type: 'entry', model: region })
  }
  return nodes
}
