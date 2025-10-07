import styles from './styles.module.scss'
import { useCallback } from "react"
import { useGetExposureDataTypesQuery } from "../../store/api/openapi"
import { homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch } from "../../store/hooks"
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

  const changeType = useCallback((type: DataType) => {
    changeCurrentQuicklook(`${type}:${exposureId}`)
    dispatch(homeSlice.actions.setDataSource(type))
  }, [changeCurrentQuicklook, dispatch, exposureId])

  const buttonConfigs = [
    { type: 'raw', label: 'Raw' },
    { type: 'post_isr_image', label: 'Post-ISR' },
    { type: 'preliminary_visit_image', label: 'Preliminary' }
  ] as const

  return (
    <>
      {buttonConfigs.map(({ type, label }) => (
        <button
          key={type}
          className={classNames(currentType === type && styles.selectedType)}
          disabled={!types.includes(type as DataType)}
          onClick={() => changeType(type as DataType)}
        >
          {label}
        </button>
      ))}
    </>
  )
}
