import { createSlice, nanoid } from "@reduxjs/toolkit"
import { V4 } from "@stellar-globe/stellar-globe"

type State = {
  dialogVisible: boolean
  images: FitsImage[]
}

type FitsImage = {
  id: string
  name: string
  url: string
  hduIndex: number
  maskConfig: MaskConfig
}

type MaskConfig = {
  maskBit: number
  color: V4
}

function initialState(): State {
  return {
    dialogVisible: false,
    // dialogVisible: false,
    images: [
      // {
      //   hduIndex: 0,
      //   id: '1',
      //   name: 's23b-deblend',
      //   maskConfig: { maskBit: 8, color: [1, 0, 1, 1] },
      //   url: '../niu/s23b-mask/'
      // },
    ],
  }
}

export const fitsImageSlice = createSlice({
  name: 'fitsImage',
  initialState,
  reducers: create => ({
    dialogToggled: (state) => {
      state.dialogVisible = !state.dialogVisible
    },
    imageAdded: create.preparedReducer(
      ({ id: _id, ...rests }: PartiallyPartial<FitsImage, 'id'>) => {
        const id = _id ?? nanoid()
        return {
          payload: { id, ...rests },
        }
      },
      (state, { payload: { id, ...rests } }) => {
        if (!state.images.find(r => r.id === id)) {
          state.images.push({ ...rests, id })
          state.dialogVisible = true
        }
      },
    ),
    imageRemoved: create.reducer<{ id: string }>((state, { payload: { id } }) => {
      state.images = state.images.filter(r => r.id !== id)
    }),
    imageMaskConfigUpdated: create.reducer<{ id: string, maskConfig: Partial<MaskConfig> }>((state, { payload: { id, maskConfig } }) => {
      const image = state.images.find(r => r.id === id)
      if (image) {
        Object.assign(image.maskConfig, maskConfig)
      }
    }),
  }),
})


type PartiallyPartial<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>
