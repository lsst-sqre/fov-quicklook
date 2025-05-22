import { createSlice } from "@reduxjs/toolkit"
import { makeLocalStorageAccessor } from "../../utils/localStorage"

type State = {
  templates: CopyTemplate[]
}

const CopyTemplateLocalStorage = makeLocalStorageAccessor<CopyTemplate[]>('copyTemplates', defaultCopyTemplates())

export type CopyTemplate = {
  name: string
  template: string
  isUrl: boolean
}


function initialState(): State {
  const templates = CopyTemplateLocalStorage.get()
  if (templates.length === 0) {
    return { templates: defaultCopyTemplates() }
  }
  return { templates }
}


export const copyTemplateSlice = createSlice({
  name: 'copyTemplate',
  initialState: initialState(),
  reducers: {
    removeTemplate: (state, action: { payload: CopyTemplate }) => {
      state.templates = state.templates.filter((t) => t.name !== action.payload.name)
      CopyTemplateLocalStorage.set(state.templates)
    },
    updateTemplate: (state, action: { payload: CopyTemplate }) => {
      const idx = state.templates.findIndex((t) => t.name === action.payload.name)
      if (idx === -1) {
        state.templates.push(action.payload)
      } else {
        state.templates[idx] = action.payload
        CopyTemplateLocalStorage.set(state.templates)
      }
    },
    resetToDefault: (state) => {
      state.templates = defaultCopyTemplates()
      CopyTemplateLocalStorage.set(state.templates)
    },
  },
})


function defaultCopyTemplates(): CopyTemplate[] {
  return [
    {
      name: 'UUID',
      template: "%(uuid)",
      isUrl: false,
    },
    {
      name: 'Data ID for Butler',
      template: "{'exposure': %(exposure), 'detector': %(detector)}",
      isUrl: false,
    },
    {
      name: 'Butler Snippet',
      template: `from lsst.daf.butler import Butler
butler = Butler('embargo')
dataId = {'exposure': %(exposure), 'detector': %(detector)}
data = butler.get('%(dataType)', dataId)
`,
      isUrl: false,
    },
    {
      name: 'LSSTCam/Calexp mosaic',
      // https://usdf-rsp.slac.stanford.edu/rubintv/summit-usdf/lsstcam/event?key=lsstcam/2025-05-15/calexp_mosaic/000086/lsstcam_calexp_mosaic_2025-05-15_000086.jpg
      template: 'https://usdf-rsp.slac.stanford.edu/rubintv/summit-usdf/lsstcam/event?key=lsstcam/%(day_obs|iso8601)/calexp_mosaic/%(exposure|sequence|zeropadding(6))/lsstcam_calexp_mosaic_%(day_obs|iso8601)_%(exposure|sequence|zeropadding(6)).jpg',
      isUrl: true,
    }
  ]
}
