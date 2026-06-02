import { createSlice } from "@reduxjs/toolkit"
import { makeLocalStorageAccessor } from "../../utils/localStorage"
import { ButlerScopeConfig, SystemInfo } from "../api/openapi"
import { getSystemInfoSync } from "../../systemInfo"

type State = {
  templates: CopyTemplate[]
  butlerScopes: ButlerScopeConfig[]
  queryBuilderInputMode: "select" | "combobox"
}

const copyTemplateLocalStorage = makeLocalStorageAccessor<CopyTemplate[]>('copyTemplates', [])

const localTemplatesStorage = {
  get: (): CopyTemplate[] => {
    return copyTemplateLocalStorage.get().map(t => ({ ...t, isLocal: true }))
  },
  set: (templates: CopyTemplate[]): void => {
    const localTemplates = templates.filter(t => t.isLocal)
    copyTemplateLocalStorage.set(localTemplates)
  },
  remove: (): void => {
    copyTemplateLocalStorage.remove()
  }
}

export type CopyTemplate = SystemInfo['context_menu_templates'][number] & {
  isLocal?: boolean
}


function initialState(systemInfo?: SystemInfo): State {
  const templates: CopyTemplate[] = [
    ...systemInfo?.context_menu_templates ?? [],
    ...localTemplatesStorage.get(),
  ]
  return { 
    templates, 
    butlerScopes: systemInfo?.butler_scopes ?? [],
    queryBuilderInputMode: normalizeQueryBuilderInputMode(systemInfo?.query_builder_input_mode),
  }
}

export { initialState as copyTemplateInitialState }

function normalizeQueryBuilderInputMode(value: string | undefined): "select" | "combobox" {
  return value === "combobox" ? "combobox" : "select"
}


export const copyTemplateSlice = createSlice({
  name: 'copyTemplate',
  initialState,
  reducers: {
    removeTemplate: (state, action: { payload: CopyTemplate }) => {
      state.templates = state.templates.filter((t) => t.name !== action.payload.name)
      localTemplatesStorage.set(state.templates)
    },
    updateTemplate: (state, action: { payload: CopyTemplate }) => {
      const idx = state.templates.findIndex((t) => t.name === action.payload.name)
      if (idx === -1) {
        state.templates.push({ ...action.payload, isLocal: true })
      } else {
        state.templates[idx] = action.payload
        localTemplatesStorage.set(state.templates)
      }
    },
    resetToDefault: (state) => {
      const systemInfo = getSystemInfoSync()
      state.templates = systemInfo.context_menu_templates
      localTemplatesStorage.set(state.templates)
    },
  },
})
