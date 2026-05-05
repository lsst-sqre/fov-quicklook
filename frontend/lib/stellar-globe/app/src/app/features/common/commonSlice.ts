import { createSlice, PayloadAction } from "@reduxjs/toolkit"
import { TractTileLayer$ } from "@stellar-globe/react-stellar-globe"
import { AngleUnit } from "../../../common/utils/formatAngle"
import { readStorageState } from "../../store/stateSync/StorageSync"


type MagFilter = NonNullable<Parameters<typeof TractTileLayer$>[0]['magFilter']>


type State = {
  angleUnit: AngleUnit
  dialogPositionHint: PositionHint
  active: boolean,
  magFilter?: MagFilter
}


function initialState(): State {
  return {
    angleUnit: readStorageState().angleUnit ?? 'sexadecimal',
    magFilter: readStorageState().magFilter ?? 'linear',
    dialogPositionHint: readStorageState().dialogPositionHint ?? { top: 8, right: 8 },
    active: true,
  }
}


export const commonSlice = createSlice({
  name: 'common',
  initialState,
  reducers: {
    unitChanged(state, { payload: { angleUnit } }: PayloadAction<{ angleUnit: AngleUnit }>) {
      state.angleUnit = angleUnit
    },
    unitToggled(state) {
      state.angleUnit = ({
        sexadecimal: 'degree',
        degree: 'radian',
        radian: 'sexadecimal',
      } as const)[state.angleUnit]
    },
    dialogPositionHintChanged(state, { payload: positionHint }: PayloadAction<PositionHint>) {
      state.dialogPositionHint = positionHint
    },
    activeChanged(state, { payload: active }: PayloadAction<boolean>) {
      state.active = active
    },
    magFilterChanged(state, { payload: { magFilter } }: PayloadAction<{ magFilter: MagFilter }>) {
      state.magFilter = magFilter
    },
  },
})


type PositionHint = Partial<Record<'top' | 'bottom' | 'left' | 'right', number>>
