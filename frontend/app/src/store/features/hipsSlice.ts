import { createSlice } from "@reduxjs/toolkit"


type State = {
  repository: string | undefined
  notes: string
}


function initialState(): State {
  return {
    repository: undefined,
    notes: '',
  }
}


export const hipsSlice = createSlice({
  name: "hips",
  initialState,
  reducers: {
    setRepository: (state, action) => {
      state.repository = action.payload
    },
    addNotes: (state, action) => {
      state.notes += `${action.payload}\n`
    },
  },
})
