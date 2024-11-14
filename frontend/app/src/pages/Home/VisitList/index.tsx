import styles from './styles.module.scss'
import { memo, useEffect } from "react"
import { ListVisitsApiResponse, useListVisitsQuery } from "../../../store/api/openapi"
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import classNames from 'classnames'
import { homeSlice } from '../../../store/features/homeSlice'


type VisitListProps = {
  style?: React.CSSProperties
}


export const VisitList = memo(({ style }: VisitListProps) => {
  const { data: list } = useListVisitsQuery()
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const dispatch = useAppDispatch()

  useEffect(() => {
    if (currentQuicklook === undefined && list?.length) {
      dispatch(homeSlice.actions.setCurrentQuicklook(list[0].name))
    }
  }, [dispatch, list, currentQuicklook])

  return (
    <div className={styles.list} style={style}>
      {list?.map((entry) => (
        <VisitListEntry key={entry.name} entry={entry} />
      ))}
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
