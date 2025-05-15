import { createSlice } from "@reduxjs/toolkit"


type State = {
  repository: string | undefined
}


function initialState(): State {
  return {
    repository: undefined,
  }
}


export const hipsSlice = createSlice({
  name: "hips",
  initialState,
  reducers: {
    setRepository: (state, action) => {
      state.repository = action.payload
    },
  },
})
