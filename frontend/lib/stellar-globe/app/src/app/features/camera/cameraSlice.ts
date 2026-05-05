import { createSelector, createSlice, PayloadAction } from "@reduxjs/toolkit"
import { cameraCenter, CameraMode } from "@stellar-globe/stellar-globe"
import { readHashState } from "../../store/stateSync/hashSync"
import { readStorageState } from "../../store/stateSync/StorageSync"


export type CameraParams = Record<'theta' | 'phi' | 'roll' | 'za' | 'zd' | 'zp' | 'fovy', number>


type State = {
  projection: CameraMode
  retina: boolean
  params: CameraParams
}


const initialCameraParams: CameraParams = {
  fovy: 2,
  theta: 0,
  phi: 0,
  roll: 0,
  za: 0,
  zd: Math.PI / 2,
  zp: 0,
}


function initialState(): State {
  return {
    retina: readStorageState().retina ?? false,
    projection: readHashState().projection ?? 'STEREOGRAPHIC',
    params: readHashState().cameraParams ?? initialCameraParams,
  }
}


export const cameraSlice = createSlice({
  name: 'camera',
  initialState,
  reducers: {
    projectionUpdated(state, { payload: projection }: PayloadAction<CameraMode>) {
      state.projection = projection
    },
    retinaToggled(state) {
      state.retina = !state.retina
    },
    paramsChanged(state, { payload: params }: PayloadAction<CameraParams>) {
      state.params = params
    },
  },
  selectors: {
    center: createSelector(
      [
        (state: State) => state.params,
      ],
      params => cameraCenter(params),
    ),
  }
})
