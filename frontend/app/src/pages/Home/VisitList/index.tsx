import classNames from 'classnames'
import { memo, useEffect, useMemo } from "react"
import { MaterialSymbol } from '../../../components/MaterialSymbol'
import { ListVisitsApiArg, ListVisitsApiResponse, useListVisitsQuery } from "../../../store/api/openapi"
import { homeSlice } from '../../../store/features/homeSlice'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import styles from './styles.module.scss'
import { LoadingSpinner } from '../../../components/Loading'


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


export const VisitList = memo(({ style }: VisitListProps) => {
  const { list, isFetching } = useVisitList()
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const dispatch = useAppDispatch()

  useEffect(() => {
    if (currentQuicklook === undefined && list?.length) {
      dispatch(homeSlice.actions.setCurrentQuicklook(list[0].id))
    }
  }, [dispatch, list, currentQuicklook])

  return (
    <div className={styles.listWrapper}>
      <SearchBox />
      <div className={styles.listContainer}>
        <div className={styles.list} style={style}>
          {list?.map((entry) => (
            <VisitListEntry key={entry.id} entry={entry} />
          ))}
        </div>
        {isFetching && <div className={styles.loadingOverlay}><LoadingSpinner /></div>}
      </div>
    </div>
  )
})


type VisitListEntryType = ListVisitsApiResponse[number]


function VisitListEntry({ entry }: { entry: VisitListEntryType }) {
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const selected = currentQuicklook === entry.id
  const dispatch = useAppDispatch()
  const select = () => {
    dispatch(homeSlice.actions.setCurrentQuicklook(entry.id))
  }

  return (
    <div
      className={classNames(styles.entry, selected && styles.selected)}
      onClick={select}
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
