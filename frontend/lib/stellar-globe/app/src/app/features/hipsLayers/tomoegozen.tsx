import { MenuDivider, MenuItem, SubMenu } from "@szhsin/react-menu"
import { Fragment, Suspense, memo } from "react"
import { memoizeOne } from "../../../common/utils/memoizeOne"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { hipsLayersSlice } from "./hipsLayersSlice"


type TomoegozenEntry = {
  hips_id: string
  obsdate: string
  obsmonth: string
  url: string
}

function tomoegozenUrl(url: string) {
  if (import.meta.env.DEV) {
    return url.replace(/^https:\/\/tomoe\.mtk\.ioa\.s\.u-tokyo\.ac\.jp\/skyatlas\//, '/tomoegozen/')
  }
  return url
}


export const TomoegozenSubmenu = memo(() => {
  const dispatch = useAppDispatch()
  const currentBaseUrl = useAppSelector(state => state.hipsLayers.baseUrl)
  const deepestackUrl = 'https://tomoe.mtk.ioa.s.u-tokyo.ac.jp/skyatlas/data/deepstack'

  return (
    <SubMenu label="Tomo-e Gozen" overflow="auto">
      <MenuItem
        href="https://tomoe.mtk.ioa.s.u-tokyo.ac.jp"
        target="_blank"
        rel="noreferrer"
      >
        Tomo-e Gozen
      </MenuItem>
      <MenuItem
        type='checkbox'
        checked={currentBaseUrl === tomoegozenUrl(deepestackUrl)}
        onClick={() => dispatch(hipsLayersSlice.actions.baseUrlChanged({
          baseUrl: tomoegozenUrl(deepestackUrl)
        }))}
      >Deep Stack</MenuItem>
      <MenuDivider />
      <Suspense fallback={<MenuItem disabled>Loading...</MenuItem>}>
        <TomoegozenEntries />
      </Suspense>
    </SubMenu>
  )
})


setDisplayName({ TomoegozenSubmenu })


const tomoegozenEntries = (() => {
  let cache: TomoegozenEntry[] | undefined
  let promise: Promise<void> | undefined

  return () => {
    if (cache) {
      return cache
    }
    promise ??= (async () => {
      const url = tomoegozenUrl('https://tomoe.mtk.ioa.s.u-tokyo.ac.jp/skyatlas/hipslist.json')
      cache = await (await fetch(url)).json()
    })()
    throw promise
  }
})()


const groupedTomoegozenEntries = memoizeOne((entries: TomoegozenEntry[]) => {
  const g = new Map<string, TomoegozenEntry[]>()
  for (const e of entries) {
    if (!g.has(e.obsmonth)) {
      g.set(e.obsmonth, [])
    }
    g.get(e.obsmonth)!.push(e)
  }
  return [...g.entries()]
    .map(([month, entries]) => [month, entries.sort((a, b) => -a.obsdate.localeCompare(b.obsdate))] as [string, TomoegozenEntry[]])
    .sort(([a], [b]) => -a.localeCompare(b))
})


const TomoegozenEntries = memo(() => {
  const currentBaseUrl = useAppSelector(state => state.hipsLayers.baseUrl)
  const entries = tomoegozenEntries()
  const grouped = groupedTomoegozenEntries(entries)
  const dispatch = useAppDispatch()

  return (
    <Fragment>
      {grouped.map(([month, entries]) => (
        <SubMenu key={month} label={month} overflow="auto">
          {entries.map(e => (
            <MenuItem
              type='checkbox'
              checked={currentBaseUrl === tomoegozenUrl(e.url)}
              key={e.hips_id}
              onClick={() => dispatch(hipsLayersSlice.actions.baseUrlChanged({
                baseUrl: tomoegozenUrl(e.url)
              }))}
            >{e.obsdate}</MenuItem>
          ))}
        </SubMenu>
      ))}
    </Fragment>
  )
})
setDisplayName({ TomoegozenEntries })
