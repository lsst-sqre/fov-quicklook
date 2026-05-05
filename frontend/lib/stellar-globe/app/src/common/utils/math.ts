import { V3 } from "@stellar-globe/stellar-globe"


export function slerp(a: V3, b: V3, t: number): V3 {
  const cos = (
    a[0] * b[0] +
    a[1] * b[1] +
    a[2] * b[2]
  )
  if (a[0] === b[0] && a[1] === b[1] && a[2] === b[2]) {
    return a
  }
  const theta = Math.acos(Math.min(cos, 1)) / 2
  const v = 2 * t - 1
  const u = Math.tan(v * theta) / Math.tan(theta)
  const aa = (1 - u) / 2
  const bb = (1 + u) / 2
  const p: V3 = [
    aa * a[0] + bb * b[0],
    aa * a[1] + bb * b[1],
    aa * a[2] + bb * b[2],
  ]
  const r = Math.sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2])
  return [
    p[0] / r,
    p[1] / r,
    p[2] / r,
  ]
}
