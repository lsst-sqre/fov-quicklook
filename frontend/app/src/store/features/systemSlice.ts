import { createSlice } from "@reduxjs/toolkit"


type State = {
  selectedQuicklook: string | undefined
}


function initialState(): State {
  return {
    selectedQuicklook: undefined,
  }
}


export const systemSlice = createSlice({
  name: "system",
  initialState,
  reducers: {
    setSelectedQuicklook: (state, action: { payload: string | undefined }) => {
      state.selectedQuicklook = action.payload
    },
  },
})