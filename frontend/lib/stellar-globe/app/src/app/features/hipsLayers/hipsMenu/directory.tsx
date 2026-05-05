import { MenuItem, SubMenu } from "@szhsin/react-menu"
import { Fragment, Suspense, memo } from "react"
import { ErrorBoundary } from "react-error-boundary"
import { Icon } from "../../../../common/components/Icon"
import { SmallLoader } from "../../../../common/components/Loader"
import { useAppDispatch } from "../../../store/hooks"
import { parseHipsProperties } from "../HipsProperties"
import { hipsLayersSlice } from "../hipsLayersSlice"


export function HipsDirectoryMenu() {
  return (
    <ErrorBoundary fallback={<MenuItem disabled><Icon type='error' /></MenuItem>}>
      <SubMenu label="Directory">
        <Suspense fallback={<MenuItem disabled>Loading...<SmallLoader /></MenuItem>}>
          <RootDirecotry />
        </Suspense>
      </SubMenu>
    </ErrorBoundary>
  )
}


function RootDirecotry() {
  const root = useHipsDirectoryRoot()
  return (
    <Fragment>
      {root.children.map(child => (
        <HipsEntryOrDirectory key={child.id} entry={child} />
      ))}
    </Fragment>
  )
}


const HipsEntryOrDirectory = memo(({ entry }: { entry: Node }) => {
  if (entry.type === 'directory') {
    return <HipsDirectorySubMenu directory={entry} />
  }
  return <HipsEntryMenuItem entry={entry} />
})


function HipsDirectorySubMenu({ directory }: { directory: Directory }) {
  return (
    <SubMenu label={directory.name} overflow="auto">
      {directory.children.map(child => (
        <HipsEntryOrDirectory key={child.id} entry={child} />
      ))}
    </SubMenu>
  )
}


function HipsEntryMenuItem({ entry }: { entry: Entry }) {
  const dispatch = useAppDispatch()
  const onClick = () => {
    dispatch(hipsLayersSlice.actions.baseUrlChanged({ baseUrl: entry.baseUrl }))
  }
  const id = entry.id.split('/').pop()

  return (
    <MenuItem
      onClick={onClick}
    >
      {id} ({entry.title})
    </MenuItem>
  )
}


const rootCache: {
  promise?: Promise<Directory>
  error?: any
  result?: Directory
} = {}


function useHipsDirectoryRoot(): Directory {
  if (!rootCache.promise) {
    const promise = fetchHipsDirectory()
    rootCache.promise = promise
    promise.then(result => {
      rootCache.result = result
    }).catch(error => {
      rootCache.error = error
    })
  }
  const { promise, error, result } = rootCache
  if (result) {
    return result
  }
  throw error ?? promise
}


type Directory = {
  type: 'directory'
  id: string
  name: string
  children: Node[]
}


type Entry = {
  type: 'entry'
  id: string
  baseUrl: string
  title: string
}


type Node = Entry | Directory


async function fetchHipsDirectory(): Promise<Directory> {
  const url = `//alasky.cds.unistra.fr/MocServer/query?expr=(hips_frame%3Dequatorial%2Cgalactic%2Cecliptic+||+hips_frame%3D!*)+%26%26+dataproduct_type!%3Dcatalog%2Ccube+%26%26+hips_service_url%3D*&get=record`
  const response = await (await fetch(url)).text()
  const hipsTextList = response.split('\n\n')

  const root: Directory = {
    type: 'directory',
    id: '$id',
    name: '$name',
    children: [],
  }

  const hipsList = hipsTextList.map(hipsText => {
    const h = parseHipsProperties(hipsText)
    return Object.fromEntries(h.cards.map(c => [c.key, c.value]))
  })

  const mkdirForEntry = (e: Entry) => {
    const routes = e.id.split('/')
    let current = root
    for (let i = 0; i < routes.length - 1; i++) {
      const route = routes[i]
      const id = routes.slice(0, i + 1).join('/')
      let next = current.children.find(c => c.id === id && c.type === 'directory') as Directory | undefined
      if (!next) {
        next = {
          type: 'directory',
          id,
          name: route,
          children: [],
        }
        current.children.push(next)
      }
      current = next
    }
    return current
  }

  for (const h of hipsList) {
    try {
      const id = assertNotNull(h['ID'])
      const name = h['obs_title'] ?? id
      const entry: Entry = {
        type: 'entry',
        id,
        baseUrl: assertNotNull(h['hips_service_url']),
        title: name,
      }
      const parent = mkdirForEntry(entry)
      parent.children.push(entry)
    }
    catch (e) {
      console.warn(`Invalid HiPS properties: ${JSON.stringify(h)}`)
    }
  }

  const rootNode = simplifyNode(root)
  return rootNode.type === 'directory' ? rootNode : { ...root, children: [rootNode] }
}


function assertNotNull<T = any>(value: T): T {
  if (value === null || value === undefined) {
    throw new Error('Value is null or undefined')
  }
  return value
}


function simplifyNode(parent: Node): Node {
  if (parent.type === 'entry') {
    return parent
  }
  if (parent.children.length === 1) {
    const onlyChild = simplifyNode(parent.children[0])
    if (onlyChild.type === 'entry') {
      return onlyChild
    }
    return {
      ...onlyChild,
      name: `${parent.name}/${onlyChild.name}`,
    }
  }
  const children = parent.children.map(simplifyNode)
  return {
    ...parent,
    children,
  }
}
