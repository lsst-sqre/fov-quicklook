import { createSlice, PayloadAction } from "@reduxjs/toolkit"
import type { ConstellationLayer$, EsoMilkyWayLayer$ } from "@stellar-globe/react-stellar-globe"
import { hipsLayersSlice } from "../hipsLayers/hipsLayersSlice"
import { readHashState } from "../../store/stateSync/hashSync"


type ExtractProps<T extends (...args: never[]) => unknown> = Parameters<T>[0]


type State = {
  grid: {
    visible: boolean
  }
  esoMilkyWay: ExtractProps<typeof EsoMilkyWayLayer$>
  constellation: ExtractProps<typeof ConstellationLayer$>
  nearbyGalaxiesAndNebulas: {
    visible: true
  }
  hipparcosCatalog: {
    visible: boolean
  },
  tracts: {
    visible: boolean
    frame: boolean
    patch: boolean
  },
}


function initialState(): State {
  return readHashState().appearance ?? {
    grid: {
      visible: true,
    },
    esoMilkyWay: {
      visible: true,
      imageSize: 512,
    },
    constellation: {
      visible: true,
      showLines: true,
      showNames: false,
      lang: 'English',
    },
    nearbyGalaxiesAndNebulas: {
      visible: true,
    },
    hipparcosCatalog: {
      visible: true,
    },
    tracts: {
      visible: false,
      frame: false,
      patch: false,
    },
  }
}


export const appearanceLayersSlice = createSlice({
  name: 'appearanceLayers',
  initialState,
  reducers: {
    visibleToggled(state, { payload: which }: PayloadAction<keyof State>) {
      state[which].visible = !state[which].visible
    },
    propsUpdated<
      Which extends keyof State,
      Props extends Partial<State[Which]>,
    >(state: State, { payload: { which, props } }: PayloadAction<{ which: Which, props: Props }>) {
      Object.assign(state[which], props)
    },
  },
  extraReducers(builder) {
    builder.addCase(hipsLayersSlice.actions.baseUrlChanged, (state, { payload: { baseUrl } }) => {
      state.esoMilkyWay.visible = !baseUrl
    })
  },
})
