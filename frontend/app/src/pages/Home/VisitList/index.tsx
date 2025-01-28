import styles from './styles.module.scss'
import { memo, useEffect } from "react"
import { ListVisitsApiResponse, useListVisitsQuery } from "../../../store/api/openapi"
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import classNames from 'classnames'
import { homeSlice } from '../../../store/features/homeSlice'


type VisitListProps = {
  style?: React.CSSProperties
}


function isValidDate(s: string) {
  return /^[0-9]{8}$/.test(s)
}


export const VisitList = memo(({ style }: VisitListProps) => {
  const searchString = useAppSelector(state => state.home.searchString)
  const { data: list } = useListVisitsQuery({
    dayObs: isValidDate(searchString) ? Number(searchString) : undefined,
  })
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const dispatch = useAppDispatch()

  useEffect(() => {
    if (currentQuicklook === undefined && list?.length) {
      dispatch(homeSlice.actions.setCurrentQuicklook(list[0].name))
    }
  }, [dispatch, list, currentQuicklook])

  return (
    <div className={styles.listWrapper}>
      <SearchBox />
      <div className={styles.list} style={style}>
        {list?.map((entry) => (
          <VisitListEntry key={entry.name} entry={entry} />
        ))}
      </div>
    </div>
  )
})


type VisitListEntryType = ListVisitsApiResponse[number]


function VisitListEntry({ entry }: { entry: VisitListEntryType }) {
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const selected = currentQuicklook === entry.name
  const dispatch = useAppDispatch()
  const select = () => {
    dispatch(homeSlice.actions.setCurrentQuicklook(entry.name))
  }

  return (
    <div
      className={classNames(styles.entry, selected && styles.selected)}
      onClick={select}
    >
      {entry.name}
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
        placeholder='Date ex. 20241204'
        value={searchString}
        onChange={e => dispatch(homeSlice.actions.setSearchString(e.target.value))}
        style={{
          color: isValidDate(searchString) ? 'white' : 'gray',
        }}
      />
    </div>
  )
}
