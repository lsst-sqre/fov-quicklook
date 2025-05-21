import classNames from 'classnames'
import { memo, useEffect, useMemo, useRef } from "react"
import { MaterialSymbol } from '../../../components/MaterialSymbol'
import { ListVisitsApiArg, ListVisitsApiResponse, useListVisitsQuery } from "../../../store/api/openapi"
import { homeSlice } from '../../../store/features/homeSlice'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import styles from './styles.module.scss'
import { LoadingSpinner } from '../../../components/Loading'
import { useChangeCurrentQuicklook } from '../../../hooks/useChangeCurrentQuicklook'


type VisitListProps = {
  style?: React.CSSProperties
}


function isValidSearchString(s: string) {
  // 20241021 or 2024102100002
  return /^\d{8}(\d{5})?$/.test(s)
}

function useVisitList() {
  const searchString = useAppSelector(state => state.home.searchString)
  const dataSource = useAppSelector(state => state.home.dataSource)
  const query = useMemo(() => {

    if (isValidSearchString(searchString)) {
      switch (searchString.length) {
        case 8:
          return { dayObs: Number(searchString), dataType: dataSource }
        case 13:
          return { exposure: Number.parseInt(searchString), dataType: dataSource }
      }
    }
    return {
      dataType: dataSource,
    } as ListVisitsApiArg
  }, [dataSource, searchString])
  const { data: list, refetch, isFetching } = useListVisitsQuery(query)
  return { list, refetch, isFetching }
}

// exposure_timeが同等かどうかを判定する関数
function isEquivalentExposureTime(a: number, b: number): boolean {
  // 小数点第2位で四捨五入して比較
  return Math.round(a * 100) / 100 === Math.round(b * 100) / 100
}

// グループが同じかどうかを判定する関数
function isSameGroup(a: VisitListEntryType, b: VisitListEntryType): boolean {
  return a.day_obs === b.day_obs &&
    a.physical_filter === b.physical_filter &&
    isEquivalentExposureTime(a.exposure_time, b.exposure_time) &&
    a.observation_type === b.observation_type
}

// リストをグループに分割する関数
function groupVisitList(list: VisitListEntryType[] | undefined): VisitListEntryType[][] {
  if (!list || list.length === 0) return []

  const result: VisitListEntryType[][] = []
  let currentGroup: VisitListEntryType[] = [list[0]]

  for (let i = 1; i < list.length; i++) {
    if (isSameGroup(list[i - 1], list[i])) {
      currentGroup.push(list[i])
    } else {
      result.push(currentGroup)
      currentGroup = [list[i]]
    }
  }

  if (currentGroup.length > 0) {
    result.push(currentGroup)
  }

  return result
}

export const VisitList = memo(({ style }: VisitListProps) => {
  const { list, isFetching } = useVisitList()
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const dispatch = useAppDispatch()
  const changeCurrentQuicklook = useChangeCurrentQuicklook()

  // リストをグループ化
  const groupedList = useMemo(() => groupVisitList(list), [list])

  useEffect(() => {
    if (currentQuicklook === undefined && list?.length) {
      changeCurrentQuicklook(list[0].id)
    }
  }, [changeCurrentQuicklook, currentQuicklook, list])

  return (
    <div className={styles.listWrapper}>
      <SearchBox />
      <div className={styles.listContainer}>
        <div className={styles.list} style={style}>
          {groupedList.map((group, index) => (
            <VisitGroup key={index} group={group} />
          ))}
        </div>
        {isFetching && <div className={styles.loadingOverlay}><LoadingSpinner /></div>}
      </div>
    </div>
  )
})

// グループを表示するコンポーネント
function VisitGroup({ group }: { group: VisitListEntryType[] }) {
  if (!group.length) return null

  const firstEntry = group[0]
  const roundedExposureTime = Math.round(firstEntry.exposure_time * 100) / 100
  const isRounded = roundedExposureTime !== firstEntry.exposure_time
  // 丸めた値を文字列で表示（小数点以下の不要な0は表示しない）
  const exposureTimeDisplay = `${isRounded ? '~' : ''}${roundedExposureTime}`

  return (
    <div className={styles.group}>
      <div className={styles.groupHeader}>
        <div className={styles.headerItem} title="Filter">
          <span>{firstEntry.physical_filter}</span>
        </div>
        <div className={styles.headerItem} title="Exposure Time">
          <span>{exposureTimeDisplay}</span>
        </div>
        <div className={styles.headerItem} title="Type">
          <span>{firstEntry.observation_type}</span>
        </div>
        <div className={styles.headerItem} title="Program">
          <span>{firstEntry.science_program}</span>
        </div>
        <div className={styles.headerItem} title="Reason">
          <span>{firstEntry.observation_reason}</span>
        </div>
        <div className={styles.headerItem} title="Target">
          <span>{firstEntry.target_name}</span>
        </div>
      </div>
      <div className={styles.groupEntries}>
        {group.map((entry) => (
          <VisitListEntry key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  )
}

type VisitListEntryType = ListVisitsApiResponse[number]


function VisitListEntry({ entry }: { entry: VisitListEntryType }) {
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const selected = currentQuicklook?.split(':')[1] === entry.id.split(':')[1]
  const entryRef = useRef<HTMLDivElement>(null)
  const changeCurrentQuicklook = useChangeCurrentQuicklook()

  const select = () => {
    changeCurrentQuicklook(entry.id)
  }

  useEffect(() => {
    if (selected && entryRef.current) {
      entryRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      })
    }
  }, [selected])

  return (
    <div
      ref={entryRef}
      className={classNames(styles.entry, selected && styles.selected)}
      onClick={select}
      title={`obs_id: ${entry.obs_id};\nexposure_time: ${entry.exposure_time}s`}
    >
      {entry.id.split(':').slice(-1)[0]}
    </div>
  )
}


function SearchBox() {
  const dispatch = useAppDispatch()
  const searchString = useAppSelector(state => state.home.searchString)
  const dataSource = useAppSelector(state => state.home.dataSource)
  const { refetch } = useVisitList()

  return (
    <div className={styles.searchBox}>
      <div style={{ display: 'flex' }} >
        <select
          value={dataSource}
          onChange={e => dispatch(homeSlice.actions.setDataSource(e.target.value as typeof dataSource))}
          style={{
            flexGrow: 1,
          }}
        >
          <option value="raw">Raw</option>
          <option value="post_isr_image">Post-ISR (recent)</option>
          <option value="preliminary_visit_image">Preliminary PVI (recent)</option>
        </select>
        <button onClick={refetch}>
          <MaterialSymbol symbol='refresh' />
        </button>
      </div>
      <input
        type="search"
        placeholder='Date or Exposure ex. 20241204 or 2024120400003'
        value={searchString}
        onChange={e => dispatch(homeSlice.actions.setSearchString(e.target.value))}
        style={{
          color: isValidSearchString(searchString) ? 'white' : 'gray',
        }}
      />
    </div>
  )
}
