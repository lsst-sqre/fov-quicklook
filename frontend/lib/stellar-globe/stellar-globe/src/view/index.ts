import { MvpMatrix } from "./MvpMatrix"

export type View = {
  readonly mvp: MvpMatrix
  readonly lodBias: number
  readonly pixelRatio: number
  readonly drawingBufferHeight: number
}
