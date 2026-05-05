import { createSelector, createSlice, PayloadAction } from "@reduxjs/toolkit"
import { TractTileLayer } from "@stellar-globe/stellar-globe"
import { env } from "../../env"
import { readHashState } from "../../store/stateSync/hashSync"


type ColorParams = ReturnType<typeof TractTileLayer.defaultParams>


type Layer = {
  name: string
  baseUrl: string
  visible: boolean
}


type State = {
  colorParams: ColorParams
  layers: Layer[]
  toneDialogVisible: boolean
}


export const defaultFilters = ['i', 'r', 'g']


function layerVisible(layerName: string) {
  switch (env().target) {
    case 'u2k':
      return (readHashState().datasets ?? ['U2K V2']).includes(layerName)
    case 'internal':
      return (readHashState().datasets ?? ['s23b Wide', 's23b Deep']).includes(layerName)
    default:
      return (readHashState().datasets ?? ['PDR3 Wide', 'PDR3 DUD']).includes(layerName)
  }
}


function layerDef(name: string, baseUrl: string) {
  return {
    name,
    baseUrl,
    visible: layerVisible(name),
  }
}


function initialState(): State {
  const layers: State['layers'] = [
    layerDef('s23b Wide', "../data/s23b_wide"),
    layerDef('s23b Deep', "../data/s23b_deep"),
    layerDef('PDR3 Wide', "//hscmap.mtk.nao.ac.jp/hscMap4/data/pdr3_wide"),
    layerDef('PDR3 DUD', "//hscmap.mtk.nao.ac.jp/hscMap4/data/pdr3_dud"),
  ]
  if (env().data.u2k) {
    layers.push(layerDef('U2K V2', "./data/u2k_v2"))
  }
  if (env().data.la2016) {
    layers.push(layerDef('Legacy Archive 2016', "//hscmap.mtk.nao.ac.jp/hscMap4/data/la2016"))
  }
  if (env().data.la2020) {
    layers.push(layerDef('Legacy Archive 2020', "http://133.40.210.1:8000/la-Dn7Qd9L5CMAAi4OsIh0A/la"))
  }

  return {
    toneDialogVisible: true,
    colorParams: readHashState().tractTileLayerColorParams ?? TractTileLayer.defaultParams({ filters: defaultFilters }),
    layers,
  }
}


export const tractTileLayersSlice = createSlice({
  name: 'tractTileLayers',
  initialState,
  reducers: {
    colorParamsUpdated(state, { payload: { params } }: PayloadAction<{ params: ColorParams }>) {
      state.colorParams = params
    },
    layerToggled(state, { payload: { name, visible } }: PayloadAction<{ name: string, visible: boolean }>) {
      const l = state.layers.find(l => l.name === name)
      if (l) {
        l.visible = visible
      }
    },
    toneDialogToggled(state, { payload: { open } }: PayloadAction<{ open?: boolean }>) {
      state.toneDialogVisible = open ?? !state.toneDialogVisible
    },
    layerAdded(state, { payload: { name, baseUrl } }: PayloadAction<{ name: string, baseUrl: string }>) {
      state.layers.push({ name, baseUrl, visible: true })
    },
    layerRemoved(state, { payload: { name } }: PayloadAction<{ name: string }>) {
      const index = state.layers.findIndex(l => l.name === name)
      if (index >= 0) {
        state.layers.splice(index, 1)
      }
    },
  },
  selectors: {
    activeLayers: createSelector(
      [
        (state: State) => state.layers,
      ],
      layers => layers.filter(l => l.visible),
    ),
  }
})
