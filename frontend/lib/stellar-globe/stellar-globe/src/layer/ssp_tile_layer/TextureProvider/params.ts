import { V3 } from "~/types"


const defaultFilters = ['HSC-I', 'HSC-R', 'HSC-G']

function sdssTrueColor({ filters }: { filters: string[] }) {
  return {
    type: 'sdssTrueColor' as const,
    filters,
    sdssTrueColor: {
      beta: 30000.,
      a: 1,
      bias: 0.05,
      b0: 0,
    },
  }
}

function simpleRgb({ filters }: { filters: string[] }) {
  return {
    type: 'simpleRgb' as const,
    filters,
    simpleRgb: {
      beta: 30000.,
      a: 1,
      bias: 0.05,
      b0: 0,
    },
  }
}

function simpleColorMatrix({ filters }: { filters: string[] }) {
  return {
    type: 'simpleColorMatrix' as const,
    filters,
    simpleColorMatrix: {
      colors: [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ] as MatrixColor[],
      beta: 30000.,
      a: 1,
      bias: 0.05,
      b0: 0,
    },
  }
}

function sdssTrueColorMatrix({ filters }: { filters: string[] }) {
  return {
    type: 'sdssTrueColorMatrix' as const,
    filters,
    sdssTrueColorMatrix: {
      colors: [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ] as MatrixColor[],
      beta: 30000.,
      a: 1,
      bias: 0.05,
      b0: 0,
    },
  }
}

const defaultParams = {
  simpleRgb,
  simpleColorMatrix,
  sdssTrueColor,
  sdssTrueColorMatrix,
}

export type SspTileMixerType = keyof typeof defaultParams

type ParamsMap = {
  [K in SspTileMixerType]: ReturnType<(typeof defaultParams)[K]>
}

export type SspTileParams = ParamsMap[SspTileMixerType]

export type SspTileParamsOf<
  T extends SspTileMixerType
> = T extends "simpleRgb" ? ReturnType<(typeof defaultParams)[T]>["simpleRgb"] :
  T extends "simpleColorMatrix" ? ReturnType<(typeof defaultParams)[T]>["simpleColorMatrix"] :
  T extends "sdssTrueColor" ? ReturnType<(typeof defaultParams)[T]>["sdssTrueColor"] :
  T extends "sdssTrueColorMatrix" ? ReturnType<(typeof defaultParams)[T]>["sdssTrueColorMatrix"] : never


export function sspTileDefaultParams({
  type = 'sdssTrueColor',
  filters = defaultFilters,
}: {
  type?: SspTileMixerType
  filters?: string[]
} = {}): SspTileParams {
  return {
    ...defaultParams[type]({ filters }),
  }
}

export function sspTileParamsAssertType<T extends SspTileMixerType>(params: SspTileParams, type: T): asserts params is ParamsMap[T] {
  if (params.type !== type) {
    throw new Error(`SspTileLayerParams: type mismatch: expected=${type}, but actual: ${params.type}`)
  }
}

type MatrixColor = V3
