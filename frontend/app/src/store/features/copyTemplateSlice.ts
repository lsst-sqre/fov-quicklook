import { createSlice } from "@reduxjs/toolkit"
import { makeLocalStorageAccessor } from "../../utils/localStorage"

type State = {
  templates: CopyTemplate[]
}

const CopyTemplateLocalStorage = makeLocalStorageAccessor<CopyTemplate[]>('copyTemplates', defaultCopyTemplates())

export type CopyTemplate = {
  name: string
  template: string
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
  },
})


function defaultCopyTemplates(): CopyTemplate[] {
  return [
    {
      name: 'dataId',
      template: "{'exposure': %(exposure), 'detector': %(detector)}",
    },
    {
      name: 'butler',
      template: `from lsst.daf.butler import Butler
butler = Butler('/path/to/butler/repo')
dataId = {'exposure': %(exposure), 'detector': %(detector)}
data = butler.get('%(dataType)', dataId)
`
    },
  ]
}
