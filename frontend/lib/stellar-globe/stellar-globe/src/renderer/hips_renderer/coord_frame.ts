import { mat3, vec3 } from 'gl-matrix'
import { V3 } from '~/types'

// Reconsidering the Galactic coordinate system
// J.-C. Liu, Z. Zhu, and H. Zhang
// A&A 526, A16 (2011)
// https://www.aanda.org/articles/aa/pdf/2011/02/aa14961-10.pdf
const g2e = mat3.fromValues( // N_J (9)
  -0.054875539390, -0.873437104725, -0.483834991775,
  +0.494109453633, -0.444829594298, +0.746982248696,
  -0.867666135681, -0.198076389622, +0.455983794523,
)

export class CoordFrame {
  readonly invMat: mat3

  constructor(readonly mat: mat3) {
    this.invMat = mat3.transpose(mat3.create(), mat)
  }

  rotate(v: V3) {
    return vec3.transformMat3([0, 0, 0] as any, v, this.mat) as any as V3
  }

  invert(v: V3) {
    return vec3.transformMat3([0, 0, 0] as any, v, this.invMat) as any as V3
  }

  static readonly GALACTIC = new CoordFrame(g2e)
  static readonly EQUATORIAL = new CoordFrame(mat3.identity(mat3.create()))
}
