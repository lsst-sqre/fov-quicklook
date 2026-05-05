export const DELTA_MAP_N = 64 // This value must equal to valeu of DELTA_MAP_N in frag.glsl.

export type ShiftmapRequest = {
  id: number
}

export type Shiftmap = {
  id: number
  arraybuffer: ArrayBuffer
}

export type ShiftmapResponse = Shiftmap[]
