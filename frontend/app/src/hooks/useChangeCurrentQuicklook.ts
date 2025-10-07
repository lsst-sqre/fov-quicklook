import { useCallback, useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { homeSlice } from "../store/features/homeSlice"
import { useAppDispatch } from "../store/hooks"

export function useChangeCurrentQuicklook() {
  const navigate = useNavigate()
  const { visitId } = useParams()
  const dispatch = useAppDispatch()

  useEffect(() => {
    if (visitId) {
      dispatch(homeSlice.actions.setCurrentQuicklook(visitId))
    }
  }, [dispatch, visitId])

  return useCallback((quicklook: string) => {
    if (quicklook !== undefined) {
      navigate(`/visits/${quicklook}`)
    }
  }, [navigate])
}
