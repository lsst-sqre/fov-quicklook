import { useDispatch, useSelector } from 'react-redux'
import type { AppState, AppDispatch } from './'

export const useAppDispatch = useDispatch.withTypes<AppDispatch>()
export const useAppSelector = useSelector.withTypes<AppState>()
