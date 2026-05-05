import { createSelector, createSlice, PayloadAction } from "@reduxjs/toolkit"
import { SkyCoord } from "@stellar-globe/stellar-globe"

type State = {
  mouseCoord: [number, number]
}

const initialState: State = {
  mouseCoord: [Number.NaN, Number.NaN],
}

export const indicatorSlice = createSlice({
  name: 'indicator',
  initialState,
  reducers: {
    mouseCoordUpdated(state, { payload: coord }: PayloadAction<[number, number]>) {
      state.mouseCoord = coord
    },
  },
  selectors: {
    // coord: (state: State) => SkyCoord.fromRad(...state.coord),
    coord: createSelector(
      (state: State) => state.mouseCoord,
      (coord) => SkyCoord.fromRad(...coord)
    ),
  }
})
