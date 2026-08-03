import ccdNameTable from './ccdname-table.json'
// grep LSSTCam ../../backend/src/quicklook/datasource/butler_datasource/ccd-name-map.txt | perl -nae 'END { print "}" } print ",\"$F[1]\":\"$F[2]\""' | sed 's/^,/{/g' | python -m json.tool > src/store/features/ccdname-table.json
import { createSlice, PayloadAction } from "@reduxjs/toolkit"
import { angle, V2 } from "@stellar-globe/stellar-globe"
import { initialSearchParams } from "../../hooks/useHashSync"
import { buildScopeId } from "../../quicklookId"
import { RubinImageFilter, RubinImageFilterParams } from "../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImageFilter"
import { ListVisitsApiArg, SystemInfo } from "../api/openapi"

export type ButlerScopeId = string

type State = {
  currentQuicklook: string | undefined
  cameraRevision: number
  cameraParams: CameraParams
  mouseCursorClientCoord: V2
  lineProfiler: LineProfilerState
  filterParams: RubinImageFilterParams
  searchString: string
  dataSource: ButlerScopeId
  showFrame: boolean
  showCompactStatus: boolean
  showMemoryUsageInCompactStatus: boolean
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

function initialState(systemInfo?: SystemInfo): State {
  const scope = systemInfo?.butler_scopes?.[0]
  const defaultDataSource = scope?.id
    ? scope.id as ButlerScopeId
    : (scope ? buildScopeId({
      repositoryName: scope.repository_name ?? "embargo",
      collection: scope.collection,
      datasetType: scope.dataset_type,
    }) : '' as ButlerScopeId)
  return {
    currentQuicklook: undefined,
    cameraRevision: 0,
    mouseCursorClientCoord: [0, -1],
    lineProfiler: {
      enabled: true,
    },
    filterParams: initialSearchParams.filterParams ?? RubinImageFilter.defaultParams(),
    searchString: '',
    dataSource: defaultDataSource,
    showFrame: true,
    showCompactStatus: false,
    showMemoryUsageInCompactStatus: false,
    cameraParams: initialSearchParams.cameraParams ?? initialCameraParams,
    hilightedCcdId: initialHightlightCcds(),
    listGroupingTimeToleranceDigits: 2,
  }
}

export { initialState as homeInitialState }

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
    setDataSource: (state, action: PayloadAction<ButlerScopeId>) => {
      state.dataSource = action.payload
    },
    setShowFrame: (state, action: PayloadAction<boolean>) => {
      state.showFrame = action.payload
    },
    setShowCompactStatus: (state, action: PayloadAction<boolean>) => {
      state.showCompactStatus = action.payload
    },
    setShowMemoryUsageInCompactStatus: (state, action: PayloadAction<boolean>) => {
      state.showMemoryUsageInCompactStatus = action.payload
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
    setHighlightCcds: (state, action: PayloadAction<string[]>) => {
      state.hilightedCcdId = action.payload
    },
    setListGroupingTimeToleranceDigits: (state, action: PayloadAction<number>) => {
      state.listGroupingTimeToleranceDigits = action.payload
    },
  },
})


function initialHightlightCcds(): string[] {
  return readHighlightedCcds(new URLSearchParams(window.location.search))
}


export function hasExplicitDetectorSelection(searchParams: URLSearchParams) {
  return searchParams.has('detector') || searchParams.has('detectors')
}


export function readHighlightedCcds(searchParams: URLSearchParams): string[] {
  const single = searchParams.get('detector')
  if (single) {
    return [parseDetectorName(single)]
  }

  const serialized = searchParams.get('detectors')
  if (!serialized) return []
  try {
    return serialized.split(',').map((s) => s.trim()).filter((s) => s.length > 0).map(parseDetectorName)
  }
  catch (e) {
    return []
  }
}


export function writeHighlightedCcds(searchParams: URLSearchParams, ccds: string[]) {
  const next = new URLSearchParams(searchParams)
  next.delete('detector')
  next.delete('detectors')

  if (ccds.length === 1) {
    next.set('detector', ccds[0])
  }
  else if (ccds.length > 1) {
    next.set('detectors', ccds.join(','))
  }

  return next
}


export function parseDetectorName(name: string) {
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
