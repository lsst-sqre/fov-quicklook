import styles from './styles.module.scss'
import { useCallback } from "react"
import { useGetExposureDataTypesQuery } from "../../store/api/openapi"
import { buildVisitId, extractScopeIdFromVisitId, getSingleDimensionName, getSingleDimensionValue, parseScopeId } from "../../quicklookId"
import { homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { useHomeContext } from "./context"
import classNames from 'classnames'
import { useChangeCurrentQuicklook } from '../../hooks/useChangeCurrentQuicklook'

export function DataTypeSwitch() {
  const { currentQuicklook } = useHomeContext()
  const currentId = currentQuicklook.id
  const exposureDimension = currentId ? getSingleDimensionName(currentId) : undefined
  const exposureValue = currentId ? getSingleDimensionValue(currentId) : undefined
  const exposureId = exposureDimension === "exposure" && exposureValue?.match(/^\d+$/) ? Number(exposureValue) : undefined
  const currentType = currentId ? extractScopeIdFromVisitId(currentId) : undefined
  const { data, isFetching } = useGetExposureDataTypesQuery({ id: exposureId! }, {
    skip: !exposureId,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
  })
  const types = (isFetching ? [] : data) ?? []
  const dispatch = useAppDispatch()
  const changeCurrentQuicklook = useChangeCurrentQuicklook()
  const butlerScopes = useAppSelector(state => state.copyTemplate.butlerScopes)

  const changeType = useCallback((scopeId: string) => {
    if (exposureId === undefined) return
    const visitId = buildVisitId({
      ...parseScopeId(scopeId),
      dimensions: { exposure: exposureId },
    })
    changeCurrentQuicklook(visitId)
    dispatch(homeSlice.actions.setDataSource(scopeId))
  }, [changeCurrentQuicklook, dispatch, exposureId])

  if (exposureId === undefined) {
    return null
  }

  return (
    <>
      {butlerScopes.map((scope) => {
        const key = scope.id ?? ""
        return (
          <button
            key={key}
            className={classNames(currentType === key && styles.selectedType)}
            disabled={!types.includes(key)}
            onClick={() => changeType(key)}
          >
            {scope.display_name}
          </button>
        )
      })}
    </>
  )
}
