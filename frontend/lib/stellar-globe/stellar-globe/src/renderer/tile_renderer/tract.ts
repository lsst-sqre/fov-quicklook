import { mat4, vec3, vec4 } from 'gl-matrix'
import { deg2rad, SkyCoord } from '~/lib/angle'
import { V2, V3 } from '~/types'
import { clip } from "~/utils/math"
import { serialNumber } from '~/utils/serial_number'
import { View } from '~/view/index'

type Header = { [key: string]: any }
export type TileId = string

export class Tract {
  readonly mMatrix: mat4
  readonly invMMatrix: mat4
  readonly pixelScale: number
  readonly refPoint: V3
  readonly id = serialNumber()
  readonly fov = deg2rad(1.8) // 1.8deg is for HSC
  readonly tileSize: number
  readonly minTileLevel: number
  readonly maxTileLevel: number
  readonly flipV: boolean

  constructor(
    readonly naxis1: number,       // [pixel]
    readonly naxis2: number,       // [pixel]
    readonly crval1: number,       // [rad]
    readonly crval2: number,       // [rad]
    crpix1: number,          // [pixel]
    crpix2: number,          // [pixel]
    cd: [number, number, number, number],  // [rad/pixel]
    options: {
      tileSize?: number,
      minTileLevel?: number,
      maxTileLevel?: number,
      flipV?: boolean,
    } = {},
  ) {
    this.tileSize = options.tileSize || 256
    this.minTileLevel = options.minTileLevel || 0
    this.maxTileLevel = options.maxTileLevel || 8
    const m = mat4.create()
    mat4.rotateZ(m, m, crval1)
    mat4.rotateY(m, m, -crval2)
    mat4.mul(m, m, mat4.fromValues(
      0, 1, 0, 0,
      0, 0, 1, 0,
      1, 0, 0, 0,
      1, 0, 0, 1,
    ))
    mat4.mul(m, m, [
      cd[0], cd[2], 0, 0,
      cd[1], cd[3], 0, 0,
      0, 0, 1, 0,
      0, 0, 0, 1,
    ] as any)
    mat4.translate(m, m, [- crpix1, - crpix2, 0])
    mat4.translate(m, m, [0.5, 0.5, 0])
    this.flipV = options.flipV ?? false
    if (options.flipV) {
      mat4.translate(m, m, [0, naxis2, 0])
      mat4.scale(m, m, [1, -1, 1])
    }
    this.mMatrix = m
    this.invMMatrix = mat4.invert(mat4.create(), this.mMatrix)!
    this.refPoint = SkyCoord.fromRad(crval1, crval2).xyz
    this.pixelScale = Math.sqrt(Math.abs(cd[0] * cd[3] - cd[1] * cd[2]))
    Tract.id2tract.set(this.id, this)
  }

  pixel2xyz(j: number, i: number): V3 {
    const v = vec4.transformMat4(vec4.create(), [j, i, 0, 1], this.mMatrix)
    const r = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return [v[0] / r, v[1] / r, v[2] / r]
  }

  xyz2pixel(xyz: V3): V2 {
    const sep = vec3.angle(xyz, this.refPoint)
    const r = 1 / Math.cos(sep)
    const [x, y, z] = xyz
    const pixel = vec4.transformMat4(vec4.create(), [r * x, r * y, r * z, 1], this.invMMatrix)
    return [pixel[0], pixel[1]]
  }

  pix2jacobian(x: number, y: number) {
    const xyz = this.pixel2xyz(x, y)
    const t = vec3.angle(xyz, this.refPoint)
    return 1 / Math.cos(t) ** 3
  }

  ndc2pixel(view: View, cb: (f: (ndx: number, ndy: number) => V3) => void) {
    const b = mat4.mul(mat4.create(), this.invMMatrix, view.mvp.iPv)
    //  A = pvMatrix * mMatrix
    //  (x, y, z, w) = A * (pix_x, pix_y, 0, 1)
    //
    //  p = x / w   : ndx
    //  q = y / w   : ndy
    //  r = z / w   : ndz
    //
    //  B = A**-1
    //  (pix_x, pix_y, 0, 1) = B * (x, y, z, w)
    //  => (pix_x, pix_y, 0, 1) = w * B * (p, q, r, 1) <= eq1
    //
    //  row 3 of eq1 => b31*p * b32*q + b33*r + b34 = 0
    //  => r = - (b31*p + b32*q + b34) / b33
    //  row 4 of eq1 => 1 = w * (b41*p + b42*q + b43*r + b44)
    //  => w = 1 / (b41*p + b42*q + b43*r + b44)
    //
    //      b11(0)  b12(4)  b13(8)  b14(12)
    //  B = b21(1)  b22(5)  b23(9)  b24(13)
    //      b31(2)  b32(6)  b33(10) b34(14)
    //      b41(3)  b42(7)  b43(11) b44(15)
    cb((p, q) => {
      const r = -(b[2] * p + b[6] * q + b[14]) / b[10]
      const w = 1 / ((b[3] * p) + (b[7] * q) + (b[11] * r) + b[15])
      const v = vec4.fromValues(p, q, r, 1)
      vec4.transformMat4(v, v, b)
      return [w * v[0], w * v[1], w]
    })
  }

  private static readonly noIndex = { minP: 0, maxP: -1, minQ: 0, maxQ: -1, baseLevel: -1, lodAlpha: -1 }

  tileIndices(view: View, lodBias: number) {
    // i: vertical raw pixelo axis
    // j: horizontal raw pixel axis
    // p: vertical tile index
    // q: horizontal tile index
    let minJ = Number.POSITIVE_INFINITY
    let maxJ = Number.NEGATIVE_INFINITY
    let minI = Number.POSITIVE_INFINITY
    let maxI = Number.NEGATIVE_INFINITY
    this.ndc2pixel(view, ndc2bpixel => {
      for (const [ndx, ndy] of [[-1, -1], [-1, 1], [1, -1], [1, 1]]) {
        const [j, i, w] = ndc2bpixel(ndx, ndy)
        if (w < 0) {
          return
        }
        if (j < minJ) { minJ = j }
        if (j > maxJ) { maxJ = j }
        if (i < minI) { minI = i }
        if (i > maxI) { maxI = i }
      }
    })
    if (maxJ < 0 || this.naxis1 < minJ) { return Tract.noIndex }
    if (maxI < 0 || this.naxis2 < minI) { return Tract.noIndex }
    minJ = Math.max(minJ, 0)
    maxJ = Math.min(maxJ, this.naxis1)
    minI = Math.max(minI, 0)
    maxI = Math.min(maxI, this.naxis2)
    const density = (view.mvp.arc / this.pixelScale) / view.drawingBufferHeight // (raw pixel) / (display pixel)
    const level = clip(Math.log(density) / Math.LN2 + lodBias, this.minTileLevel, this.maxTileLevel)
    const baseLevel = Math.floor(level)
    const lodAlpha = 1 - (level - baseLevel)
    const tileSize = this.tileSize << baseLevel
    const minP = Math.floor(minI / tileSize)
    const maxP = Math.floor(maxI / tileSize)
    const minQ = Math.floor(minJ / tileSize)
    const maxQ = Math.floor(maxJ / tileSize)
    return { minP, maxP, minQ, maxQ, baseLevel, lodAlpha }
  }

  static fromFitsHeader(
    h: Header,
    options: { tileSize?: number, minTileLevel?: number, maxTileLevel?: number, flipV?: boolean } = {},
  ) {
    console.assert(h.CTYPE1 === undefined || h.CTYPE1 === 'RA---TAN')
    console.assert(h.CTYPE2 === undefined || h.CTYPE2 === 'DEC--TAN')
    console.assert(h.LONPOLE === undefined)
    console.assert(h.LATPOLE === undefined)
    const { tileSize, minTileLevel, maxTileLevel, flipV } = options
    return new Tract(
      card(h, 'NAXIS1', 'number'),
      card(h, 'NAXIS2', 'number'),
      deg2rad(card(h, 'CRVAL1', 'number')),
      deg2rad(card(h, 'CRVAL2', 'number')),
      card(h, 'CRPIX1', 'number'),
      card(h, 'CRPIX2', 'number'),
      [
        deg2rad(card(h, 'CD1_1', 'number')),
        deg2rad(card(h, 'CD1_2', 'number', 0)),
        deg2rad(card(h, 'CD2_1', 'number', 0)),
        deg2rad(card(h, 'CD2_2', 'number')),
      ],
      {
        tileSize,
        minTileLevel,
        maxTileLevel,
        flipV,
      },
    )
  }

  private static id2tract = new Map<number, Tract>()
  static fromId(id: number) {
    return Tract.id2tract.get(id)!
  }

  static encodeTileId(tract: Tract, level: number, p: number, q: number): TileId {
    return `${tract.id}:${level}:${p}:${q}`
  }

  static decodeTileId(id: TileId) {
    const [tractId, level, p, q] = id.split(':').map(Number)
    const tract = Tract.fromId(tractId)
    return { tract, level, p, q }
  }

  encodeTileId(level: number, p: number, q: number) {
    return Tract.encodeTileId(this, level, p, q)
  }
}

type CardType = {
  number: number,
}

function card<T extends keyof CardType>(h: Header, key: string, type: T, defaultValue?: CardType[T]): CardType[T] {
  const v = key in h ? h[key] : defaultValue
  if (typeof v !== type) {
    throw new Error(`type mismatch: ${type} for [${key}] = ${v}`)
  }
  return v
}
