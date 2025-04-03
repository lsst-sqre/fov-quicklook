import styles from './styles.module.scss'
import { memo, useEffect, useMemo } from "react"
import { ListVisitsApiResponse, useListVisitsQuery } from "../../../store/api/openapi"
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import classNames from 'classnames'
import { homeSlice } from '../../../store/features/homeSlice'


type VisitListProps = {
  style?: React.CSSProperties
}


function isValidSearchString(s: string) {
  // 20241021 or 2024102100002
  return /^\d{8}(\d{5})?$/.test(s)
}


export const VisitList = memo(({ style }: VisitListProps) => {
  const searchString = useAppSelector(state => state.home.searchString)
  const query = useMemo(() => {
    if (isValidSearchString(searchString)) {
      switch (searchString.length) {
        case 8:
          return { dayObs: Number(searchString) }
        case 1:
          return { exposure: Number.parseInt(searchString) }
      }
    }
    return {}
  }, [searchString])

  const { data: list } = useListVisitsQuery(query)
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
      <div className={styles.list} style={style}>
        {list?.map((entry) => (
          <VisitListEntry key={entry.id} entry={entry} />
        ))}
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
      {entry.id}
    </div>
  )
}


function SearchBox() {
  const dispatch = useAppDispatch()
  const searchString = useAppSelector(state => state.home.searchString)

  return (
    <div className={styles.searchBox}>
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
