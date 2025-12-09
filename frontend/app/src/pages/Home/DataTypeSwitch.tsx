import styles from './styles.module.scss'
import { useCallback } from "react"
import { useGetExposureDataTypesQuery } from "../../store/api/openapi"
import { homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { useHomeContext } from "./context"
import classNames from 'classnames'
import { useChangeCurrentQuicklook } from '../../hooks/useChangeCurrentQuicklook'

export function DataTypeSwitch() {
  type DataType = typeof types[number]
  const { currentQuicklook } = useHomeContext()
  const exposureId = Number(currentQuicklook.id?.split(':')[1])
  const currentType = currentQuicklook.id?.split(':')[0] as DataType | undefined
  const { data, isFetching } = useGetExposureDataTypesQuery({ id: exposureId }, {
    skip: !exposureId,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
  })
  const types = (isFetching ? [] : data!) ?? []
  const dispatch = useAppDispatch()
  const changeCurrentQuicklook = useChangeCurrentQuicklook()
  const ccdDataTypes = useAppSelector(state => state.copyTemplate.ccdDataTypes)

  const changeType = useCallback((type: DataType) => {
    changeCurrentQuicklook(`${type}:${exposureId}`)
    dispatch(homeSlice.actions.setDataSource(type))
  }, [changeCurrentQuicklook, dispatch, exposureId])

  return (
    <>
      {ccdDataTypes.map(({ id, display_name }) => (
        <button
          key={id}
          className={classNames(currentType === id && styles.selectedType)}
          disabled={!types.includes(id as DataType)}
          onClick={() => changeType(id as DataType)}
        >
          {display_name}
        </button>
      ))}
    </>
  )
}
