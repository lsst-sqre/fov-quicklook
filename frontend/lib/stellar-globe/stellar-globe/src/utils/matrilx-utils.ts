import { mat3, mat4 } from 'gl-matrix'

export function composite(scales: number[], matrices: Float32Array[]): Float32Array {
  const m = mat4.fromValues(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
  for (let i = 0; i < scales.length; ++i) {
    mat4.multiplyScalarAndAdd(m, m, matrices[i] as mat4, scales[i])
  }
  // @ts-ignore
  return m
}

export function mulZenith4(m: mat4, a: number, d: number, p: number) {
  // mat4.rotateZ(m, m, -p)
  // mat4.rotateY(m, m, -(Math.PI / 2 - d))
  // mat4.rotateZ(m, m, -a)
  // return m
  const cA = Math.cos(a)
  const sA = Math.sin(a)
  const cP = Math.cos(p)
  const sP = Math.sin(p)
  const cD = Math.cos(d)
  const sD = Math.sin(d)
  mat4.mul(m, m, mat4.fromValues(
    cA * cP * sD - sA * sP, -cA * sD * sP - cP * sA, cA * cD, 0,
    cA * sP + cP * sA * sD, cA * cP - sA * sD * sP, cD * sA, 0,
    -cD * cP, cD * sP, sD, 0,
    0, 0, 0, 1))
  return m
}

export function zenith3(a: number, d: number, p: number) {
  const cA = Math.cos(a)
  const sA = Math.sin(a)
  const cP = Math.cos(p)
  const sP = Math.sin(p)
  const cD = Math.cos(d)
  const sD = Math.sin(d)
  return mat3.fromValues(
    cA * cP * sD - sA * sP, -cA * sD * sP - cP * sA, cA * cD,
    cA * sP + cP * sA * sD, cA * cP - sA * sD * sP, cD * sA,
    -cD * cP, cD * sP, sD)
}

export function izenith3(a: number, d: number, p: number) {
  const cA = Math.cos(a)
  const sA = Math.sin(a)
  const cP = Math.cos(p)
  const sP = Math.sin(p)
  const cD = Math.cos(d)
  const sD = Math.sin(d)
  return mat3.fromValues(
    cA * cP * sD - sA * sP, cA * sP + cP * sA * sD, -cD * cP,
    -cA * sD * sP - cP * sA, cA * cP - sA * sD * sP, cD * sP,
    cA * cD, cD * sA, sD,
  )
}

export function izenith4(a: number, d: number, p: number) {
  const cA = Math.cos(a)
  const sA = Math.sin(a)
  const cP = Math.cos(p)
  const sP = Math.sin(p)
  const cD = Math.cos(d)
  const sD = Math.sin(d)
  return mat4.fromValues(
    cA * cP * sD - sA * sP, cA * sP + cP * sA * sD, -cD * cP, 0,
    -cA * sD * sP - cP * sA, cA * cP - sA * sD * sP, cD * sP, 0,
    cA * cD, cD * sA, sD, 0,
    0, 0, 0, 1,
  )
}

function zenith2adp(m: mat3) {
  const d = Math.asin(m[8])
  const a = Math.atan2(m[5], m[2])
  const p = Math.atan2(m[7], -m[6])
  return [a, d, p]
}

export function normalizeZenith(a: number, d: number, z: number) {
  return zenith2adp(zenith3(a, d, z))
}
