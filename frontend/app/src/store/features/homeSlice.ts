import { createSlice, PayloadAction } from "@reduxjs/toolkit"
import { V2 } from "@stellar-globe/stellar-globe"
import { RubinImageFilter, RubinImageFilterParams } from "../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter"

type State = {
  currentQuicklook: string | undefined
  viewerCamera: ViewerCamera
  mouseCursorClientCoord: V2
  lineProfiler: LineProfilerState
  filterParams: RubinImageFilterParams
}

type ViewerCamera = object

type LineProfilerState = {
  enabled: boolean
}


function initialState(): State {
  return {
    currentQuicklook: undefined,
    viewerCamera: {},
    mouseCursorClientCoord: [0, -1],
    lineProfiler: {
      enabled: true,
    },
    filterParams: RubinImageFilter.defaultParams(),
  }
}

export const homeSlice = createSlice({
  name: "home",
  initialState,
  reducers: {
    setCurrentQuicklook: (state, action: PayloadAction<string>) => {
      state.currentQuicklook = action.payload
    },
    setViewerCamera: (state, action: PayloadAction<ViewerCamera>) => {
      state.viewerCamera = action.payload
    },
    setMouseCursorClientCoord: (state, action: PayloadAction<V2>) => {
      state.mouseCursorClientCoord = action.payload
    },
    setFilterParams: (state, action: PayloadAction<RubinImageFilterParams>) => {
      state.filterParams = action.payload
    },
    toggleLineProfiler: state => {
      state.lineProfiler.enabled = !state.lineProfiler.enabled
    },
  },
})
