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
  const parts = currentQuicklook.id?.split(':') ?? []
  const exposureId = parts[2] ? Number(parts[2]) : undefined
  const currentType = parts.length >= 3 ? `${parts[0]}:${parts[1]}` as DataType : undefined
  const { data, isFetching } = useGetExposureDataTypesQuery({ id: exposureId! }, {
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
      {ccdDataTypes.map(({ data_type, display_name, repository_name }) => {
        const key = `${repository_name}:${data_type}`
        return (
          <button
            key={key}
            className={classNames(currentType === key && styles.selectedType)}
            disabled={!types.includes(key as DataType)}
            onClick={() => changeType(key as DataType)}
          >
            {display_name}
          </button>
        )
      })}
    </>
  )
}
