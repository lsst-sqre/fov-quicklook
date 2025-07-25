import ccdNameTable from './ccdname-table.json'
// grep LSSTCam ../../backend/src/quicklook/datasource/butler_datasource/ccd-name-map.txt | perl -nae 'END { print "}" } print ",\"$F[1]\":\"$F[2]\""' | sed 's/^,/{/g' | python -m json.tool > src/store/features/ccdname-table.json
import { createSlice, PayloadAction } from "@reduxjs/toolkit"
import { angle, V2 } from "@stellar-globe/stellar-globe"
import { initialSearchParams } from "../../hooks/useHashSync"
import { RubinImageFilter, RubinImageFilterParams } from "../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter"
import { ListVisitsApiArg } from "../api/openapi"

export type CcdDataType = NonNullable<ListVisitsApiArg["dataType"]>

type State = {
  currentQuicklook: string | undefined
  cameraRevision: number
  cameraParams: CameraParams
  mouseCursorClientCoord: V2
  lineProfiler: LineProfilerState
  filterParams: RubinImageFilterParams
  searchString: string
  dataSource: CcdDataType
  showFrame: boolean
  hilightedCcdId: string[]
  listGroupingTimeToleranceDigits: number
}

export type CameraParams = Record<'theta' | 'phi' | 'roll' | 'za' | 'zd' | 'zp' | 'fovy', number>


const initialCameraParams: CameraParams = {
  fovy: angle.deg2rad(3.6),
  theta: 0,
  phi: 0,
  roll: 0,
  za: 0,
  zd: Math.PI / 2,
  zp: 0,
}

type LineProfilerState = {
  enabled: boolean
}

function initialState(): State {
  return {
    currentQuicklook: undefined,
    cameraRevision: 0,
    mouseCursorClientCoord: [0, -1],
    lineProfiler: {
      enabled: true,
    },
    filterParams: initialSearchParams.filterParams ?? RubinImageFilter.defaultParams(),
    searchString: '',
    dataSource: 'raw',
    showFrame: true,
    cameraParams: initialSearchParams.cameraParams ?? initialCameraParams,
    hilightedCcdId: initialHightlightCcds(),
    listGroupingTimeToleranceDigits: 2,
  }
}

export const homeSlice = createSlice({
  name: "home",
  initialState,
  reducers: {
    setCurrentQuicklook: (state, action: PayloadAction<string>) => {
      state.currentQuicklook = action.payload
    },
    cameraUpdated: (state, action: PayloadAction<void>) => {
      state.cameraRevision += 1
    },
    cameraParamsUpdated: (state, action: PayloadAction<CameraParams>) => {
      state.cameraParams = action.payload
      state.cameraRevision += 1
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
    setSearchString: (state, action: PayloadAction<string>) => {
      state.searchString = action.payload
    },
    setDataSource: (state, action: PayloadAction<'raw' | 'post_isr_image' | 'preliminary_visit_image'>) => {
      state.dataSource = action.payload
    },
    setShowFrame: (state, action: PayloadAction<boolean>) => {
      state.showFrame = action.payload
    },
    toggleHighlightCcd: (state, action: PayloadAction<string>) => {
      const idx = state.hilightedCcdId.indexOf(action.payload)
      if (idx === -1) {
        state.hilightedCcdId.push(action.payload)
      } else {
        state.hilightedCcdId.splice(idx, 1)
      }
    },
    clearHighlightCcd: (state) => {
      state.hilightedCcdId = []
    },
    setListGroupingTimeToleranceDigits: (state, action: PayloadAction<number>) => {
      state.listGroupingTimeToleranceDigits = action.payload
    },
  },
})


function initialHightlightCcds(): string[] {
  const searchParams = new URLSearchParams(window.location.search)
  const serialized = searchParams.get('detectors')
  if (!serialized) return []
  try {
    return serialized.split(',').map((s) => s.trim()).filter((s) => s.length > 0).map(parseDetectorName)
  }
  catch (e) {
    return []
  }
}

function parseDetectorName(name: string) {
  if (name.match(/^\d+$/)) {
    // @ts-ignore
    const translated = ccdNameTable[name] as string | undefined
    if (translated === undefined) {
      throw new Error(`Unknown detector name: ${name}`)
    }
    return translated
  } else {
    return name
  }
}
