import { V2, V3 } from '~/types'

export function clip(x: number, a: number, b: number) {
  return x < a ? a : (x > b ? b : x)
}

export function range(start: number, end?: number) {
  if (end === undefined) {
    end = start
    start = 0
  }
  const a: number[] = []
  for (let i = start; i < end; ++i) {
    a.push(i)
  }
  return a
}

export function square(x: number) {
  return x * x
}

export function thetaphi2xyz(theta: number, phi: number): V3 {
  const ct = Math.cos(theta)
  return [ct * Math.cos(phi), ct * Math.sin(phi), Math.sin(theta)]
}

export function xyz2thetaphi(x: number, y: number, z: number): V2 {
  const r2 = x * x + y * y
  if (r2 === 0) {
    return [z > 0 ? Math.PI / 2 : -Math.PI / 2, 0]
  } else {
    const PI2 = 2 * Math.PI
    const phi = (Math.atan2(y, x) + PI2) % PI2
    const theta = Math.atan2(z, Math.sqrt(r2))
    return [theta, phi]
  }
}

export function dot(a: V3, b: V3) {
  return (
    a[0] * b[0] +
    a[1] * b[1] +
    a[2] * b[2])
}

export function diff(a: V3, b: V3): V3 {
  return [
    a[0] - b[0],
    a[1] - b[1],
    a[2] - b[2]]
}
