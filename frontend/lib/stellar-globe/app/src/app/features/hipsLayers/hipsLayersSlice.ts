import { createSlice } from "@reduxjs/toolkit"
import { appStateHistoryActions } from "../../store/hooks"
import { trackAction } from "../../store/stateHistory"
import { readHashState } from "../../store/stateSync/hashSync"

type State = {
  baseUrl: string | undefined
  hipsDialogVisible: boolean
  showHipsDialogWhenBaseUrlChanged: boolean
}

function initialState(): State {
  return {
    baseUrl: readHashState().hipsBaseUrl,
    hipsDialogVisible: false,
    showHipsDialogWhenBaseUrlChanged: false,
  }
}

export const hipsLayersSlice = createSlice({
  name: 'hipsLayers',
  initialState,
  reducers: create => ({
    baseUrlChanged: create.preparedReducer(
      (payload: { baseUrl?: string }) => trackAction({ payload }, 'HiPS URL Changed'),
      (state, { payload: { baseUrl } }) => {
        state.baseUrl = baseUrl
      },
    ),
    hipsDialogToggled: create.reducer<{ open?: boolean }>((state, { payload: { open } }) => {
      state.hipsDialogVisible = open ?? !state.hipsDialogVisible
    }),
  }),
  extraReducers(builder) {
    builder.addCase(appStateHistoryActions.setState, (state, { payload: { hipsLayers } }) => {
      state.baseUrl = hipsLayers.baseUrl
    })
    builder.addMatcher(
      action => [hipsLayersSlice.actions.baseUrlChanged.type].includes(action.type),
      state => {
        if (state.baseUrl && state.showHipsDialogWhenBaseUrlChanged) {
          state.hipsDialogVisible = true
        }
      }
    )
  },
})
