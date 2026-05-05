import { mat4, vec3, vec4 } from 'gl-matrix'
import { V3 } from '~/types'
import { diff, dot } from '~/utils/math'

export class MvpMatrix {
  readonly iPv: mat4
  readonly eyePosition: V3
  readonly direction: V3
  readonly fovCenter: V3
  // readonly ed: number
  readonly up: V3
  // readonly right: V3
  readonly aspectRatio: number
  readonly fovy: number // これは視野のようなものだが、modeによって値が変わる
  readonly arc: number // これは視野のようなものだが、modeによらず安定
  readonly radius: number

  constructor(readonly pv: mat4) {
    const b = this.iPv = mat4.invert(mat4.create(), pv as mat4) || mat4.create()
    const e: V3 = // eye position
      [b[8] / b[11], b[9] / b[11], b[10] / b[11]] // eye position
    const d: V3 = // direction
      [b[12] - (b[8] * b[15]) / b[11], b[13] - (b[9] * b[15]) / b[11], b[14] - (b[10] * b[15]) / b[11]]
    // |this.direction| == 1 if pv does not have scale matrix in its factors
    const up: vec3 = [b[4] - (b[7] * b[8]) / b[11], b[5] - (b[7] * b[9]) / b[11], b[6] - (b[7] * b[10]) / b[11]]
    this.up = up
    const right = [b[0] - (b[3] * b[8]) / b[11], b[1] - (b[3] * b[9]) / b[11], b[2] - (b[3] * b[10]) / b[11]]
    // @ts-ignore
    const upLen = vec3.len(up)
    // @ts-ignore
    const AR = vec3.len(right) / upLen // aspect ratio
    const ed = vec3.dot(e, d)
    const fovy = 2 * upLen // ( / |d| )
    const t = (-ed + Math.sqrt(ed * ed - vec3.sqrLen(e) + 1)) // e + t * d : fovCenter
    const arc = fovy * t
    this.eyePosition = e
    this.direction = d
    this.aspectRatio = AR
    this.fovy = fovy
    this.arc = arc
    this.radius = this.arc * Math.sqrt(1 + AR * AR) / 2
    this.fovCenter = [e[0] + t * d[0], e[1] + t * d[1], e[2] + t * d[2]]
    // this.ed = ed
  }

  /*
  b11(00) b12(04) b13(08) b14(12)
  b21(01) b22 ...
  ...
  b41(03) b42(07) b43(11) b44(15)
  */

  ndc2xyz(ndx: number, ndy: number, ndz: number): V3 {
    const b = this.iPv
    const y4 = 1 / (b[3] * ndx + b[7] * ndy + b[11] * ndz + b[15])
    const x = vec4.transformMat4([0, 0, 0, 0] as any, [y4 * ndx, y4 * ndy, y4 * ndz, y4], b)
    return [x[0], x[1], x[2]]
  }

  ndc2sphereXYZ(ndx: number, ndy: number, safe = false, r0 = 1) {
    const p = this.ndc2xyz(ndx, ndy, -1)
    const q = this.ndc2xyz(ndx, ndy, 1)
    const s = diff(p, q)
    // a t**2 + 2*b*t + c == 0
    const a = dot(s, s)
    const b = dot(s, q)
    const c = dot(q, q) - (r0 * r0)
    const D = b * b - a * c
    const t = (- b - Math.sqrt(safe ? Math.abs(D) : D)) / a
    return [
      t * p[0] + (1 - t) * q[0],
      t * p[1] + (1 - t) * q[1],
      t * p[2] + (1 - t) * q[2],
    ] as V3
  }
}
