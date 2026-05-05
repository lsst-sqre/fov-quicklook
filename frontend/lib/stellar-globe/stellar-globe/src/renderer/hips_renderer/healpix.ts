// tslint:disable:variable-name
// TODO: cleanup !!

import { V3 } from "~/types"

const PI = Math.PI
const PI2 = 2 * Math.PI
const PI_2 = Math.PI / 2
const PI_4 = Math.PI / 4
const PI_8 = Math.PI / 8

export const hipsQuadCoeff = (() => {
  const i2xy = (() => {
    function index2xy(index: number): [number, number] {
      const i = Math.floor(index / 4)
      const j = index % 4
      const mesh = [0, 1 / 3, 2 / 3, 1]
      return [mesh[i], mesh[j]]
    }
    const a: Array<[number, number]> = []
    for (let i = 0; i < 16; ++i) {
      a.push(index2xy(i))
    }
    return a
  })()

  const za = [new Float32Array(16), new Float32Array(16), new Float32Array(16)]
  const zb = [new Float32Array(16), new Float32Array(16), new Float32Array(16)]
  const zeromat4 = new Float32Array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

  return (order: number, ipix: number) => {
    const nside = 1 << order
    const d = PI_4 / nside
    const { f, x, y } = nest2fxy(nside, ipix)
    const { t: t0, u: u0 } = fxy2tu(nside, f, x, y)
    const belt = Math.abs(u0) <= PI_4
    const isBeltEnd = (f < 4 || 8 <= f) && x + y === nside - 1
    if (isBeltEnd) {
      for (let i = 0; i < 16; ++i) {
        const [p, q] = i2xy[i]
        const t = t0 + d * (1 - q - p)
        const u = u0 + d * (p - q)
        const zaNorth = tu2za(t, u, f >= 8)
        const zaSouth = tu2za(t, u, f < 4)
        const va = za2vec(zaNorth.z, zaNorth.a)
        const vb = za2vec(zaSouth.z, zaSouth.a)
        za[0][i] = va[0]
        za[1][i] = va[1]
        za[2][i] = va[2]
        zb[0][i] = vb[0]
        zb[1][i] = vb[1]
        zb[2][i] = vb[2]
      }
      const a = [mul(B, za[0]), mul(B, za[1]), mul(B, za[2])]
      const b = [mul(B, zb[0]), mul(B, zb[1]), mul(B, zb[2])]
      return { a, b }
    } else {
      for (let i = 0; i < 16; ++i) {
        const [p, q] = i2xy[i]
        const t = t0 + d * (1 - q - p)
        const u = u0 + d * (p - q)
        // tslint:disable-next-line:no-shadowed-variable
        const { z, a } = tu2za(t, u, belt)
        const va = za2vec(z, a)
        za[0][i] = va[0]
        za[1][i] = va[1]
        za[2][i] = va[2]
      }
      const a = [mul(B, za[0]), mul(B, za[1]), mul(B, za[2])]
      const b = [zeromat4, zeromat4, zeromat4]
      return { a, b }
    }
  }
})()

function fxy2tu(nside: number, f: number, x: number, y: number) {
  const f_row = f >> 2
  const f1 = f_row + 2
  const f2 = 2 * (f % 4) - (f_row % 2) + 1
  const v = x + y
  const h = x - y
  const i = f1 * nside - v - 1
  const k = (f2 * nside + h + (8 * nside))
  const t = k / nside * PI_4
  const u = PI_2 - i / nside * PI_4
  return { t, u }
}

function tu2za(t: number, u: number, belt: boolean) {
  const abs_u = Math.abs(u)
  if (belt) {
    const z = u / (3 * PI_8)
    const a = t
    return { z, a }
  } else {
    if (abs_u >= PI_2) {
      return { z: sign(u), a: 0 }
    }
    const t_t = t % (Math.PI / 2)
    const a = t - (abs_u - PI_4) / (abs_u - PI_2) * (t_t - PI_4)
    const z = sign(u) * (1 - 1 / 3 * square(2 - 4 * abs_u / PI))
    return { z, a }
  }
}

function za2vec(z: number, a: number): V3 {
  const z2 = z * z
  const sin_theta = z2 > 1 ? -Math.sqrt(z2 - 1) : Math.sqrt(1 - z2)
  const x = sin_theta * Math.cos(a)
  const y = sin_theta * Math.sin(a)
  return [x, y, z]
}

function mul(a: Float32Array | number[], b: Float32Array | number[]) {
  const l = b.length
  const c = new Float32Array(l)
  for (let i = 0; i < l; ++i) {
    let p = 0
    for (let j = 0; j < l; ++j) {
      p += a[i + j * l] * b[j]
    }
    c[i] = p
  }
  return c
}

function dot(a: Float32Array | number[], b: Float32Array | number[]) {
  let c = 0
  for (let i = 0; i < a.length; ++i) {
    c += a[i] * b[i]
  }
  return c
}

function ab2v(a: Float32Array[], b: Float32Array[], p: number, q: number, isBeltEnd: boolean): V3 {
  const p2 = p * p
  const p3 = p2 * p
  const q2 = q * q
  const q3 = q2 * q
  if (isBeltEnd) {
    return p - q >= 0 ?
      a.map((aa) => dot([p3, p2, p, 1], mul(aa, [q3, q2, q, 1]))) as V3 :
      b.map((bb) => dot([p3, p2, p, 1], mul(bb, [q3, q2, q, 1]))) as V3
  } else {
    return a.map((aa) => dot([p3, p2, p, 1], mul(aa, [q3, q2, q, 1]))) as V3
  }
}

function beltEnd(nside: number, ipix: number) {
  const nside2 = nside * nside
  const f = Math.floor(ipix / nside2)
  const { x, y } = bit_decombine(ipix % nside2)
  return (f < 4 || 8 <= f) && x + y === nside - 1
}

export function shiftmap(order: number, ipix: number, size: number) {
  function encode(v: number) {
    const VMAX = 0.015
    return ((v / VMAX) + 1) / 2 * 256
  }

  const nside = 1 << order
  const { a, b } = hipsQuadCoeff(order, ipix)
  const d = new Uint8Array(3 * size * size)
  const isBeltEnd = beltEnd(nside, ipix)
  function dpq(p: number, q: number) {
    const v = ab2v(a, b, p, q, isBeltEnd)
    const { x, y } = vec2pixcoord(nside, ipix, v)
    const trueP = y
    const trueQ = 1 - x
    return [p - trueP, q - trueQ]
  }
  let k = 0
  for (let i = 0; i < size; ++i) {
    const q = i / (size - 1)
    for (let j = 0; j < size; ++j) {
      const p = j / (size - 1)
      const [dp, dq] = dpq(p, q)
      d[3 * k + 0] = encode(dp)
      d[3 * k + 1] = encode(dq)
      d[3 * k + 2] = 0
      ++k
    }
  }
  return d
}

export function shiftmapId(order: number, index: number) {
  const nside = 1 << order
  const nside2 = nside * nside
  const f0 = Math.floor(index / nside2)
  const f = (f0 >> 2) << 2
  const index2 = f * nside2 + (index % nside2)
  return encode_id(order, index2)
}

function vec2pixcoord(nside: number, ipix: number, v: V3) {
  const n2 = nside * nside
  const face = Math.floor(ipix / n2)
  const { z, a: a0 } = vec2za(v[0], v[1], v[2])
  const a = wrap(a0 - (face % 4 + 2.5) * PI_2, PI2) - PI + (face % 4 + 0.5) * PI_2
  const { t, u } = zaf2tu(z, a, face)
  const cfxy = nest2fxy(nside, ipix)
  const ctu = fxy2tu(nside, cfxy.f, cfxy.x, cfxy.y)
  const d = PI_4 / nside
  const dt = (face % 4 === 1 || face % 4 === 2) ?
    wrap(t, PI2) - wrap(ctu.t, PI2) :
    wrap(t + PI, PI2) - wrap(ctu.t + PI, PI2)
  const du = u - ctu.u + d
  return {
    x: (dt + du) / d / 2,
    y: (du - dt) / d / 2,
  }
}

function vec2za(x: number, y: number, z: number) {
  const r2 = x * x + y * y
  if (r2 === 0) {
    return { z: z < 0 ? -1 : 1, a: 0 }
  } else {
    const a = (Math.atan2(y, x) + PI2) % PI2
    z /= Math.sqrt(z * z + r2)
    return { z, a }
  }
}

function nest2fxy(nside: number, ipix: number) {
  const nside2 = nside * nside
  const f = Math.floor(ipix / nside2) // base pixel index
  const k = ipix % nside2   // nested pixel index in base pixel
  const { x, y } = bit_decombine(k)
  return { f, x, y }
}

function sigma(z: number): number {
  if (z < 0) {
    return -sigma(-z)
  } else {
    return 2 - Math.sqrt(3 * (1 - z))
  }
}

function zaf2tu(z: number, a: number, f: number) {
  if (Math.abs(z) <= 2. / 3.) { // equatorial belt
    const t = a
    const u = 3 * PI_8 * z
    return { t, u }
  } else { // polar caps
    f %= 4
    // a = clamp(a, f * PI_2, (f + 1) * PI_2)
    const p_t = a - (f * PI_2)
    const sigma_z = sigma(z)
    const t = a - (Math.abs(sigma_z) - 1) * (p_t - PI_4)
    const u = PI_4 * sigma_z
    return { t, u }
  }
}

function wrap(x: number, p: number) {
  return x < 0 ? p - (-x % p) : x % p
}
function square(x: number) {
  return x * x
}
const sign: (x: number) => number = (Math as any).sign || ((x: number) => {
  return x > 0 ? 1 : (x < 0 ? -1 : 0)
})

function bit_decombine(p: number) {
  assert(p <= 0x7fffffff)
  // (python)
  // ' | '.join(f'(p & 0x{2**(2*i):x}) >> {i}' for i in range(16))
  const x = (p & 0x1) >> 0 | (p & 0x4) >> 1 | (p & 0x10) >> 2 |
    (p & 0x40) >> 3 | (p & 0x100) >> 4 | (p & 0x400) >> 5 |
    (p & 0x1000) >> 6 | (p & 0x4000) >> 7 | (p & 0x10000) >> 8 |
    (p & 0x40000) >> 9 | (p & 0x100000) >> 10 | (p & 0x400000) >> 11 |
    (p & 0x1000000) >> 12 | (p & 0x4000000) >> 13 | (p & 0x10000000) >> 14 | (p & 0x40000000) >> 15
  // (python)
  // ' | '.join(f'(p & 0x{2**(2*i + 1):x}) >> {i+1}' for i in range(15))
  const y = (p & 0x2) >> 1 | (p & 0x8) >> 2 | (p & 0x20) >> 3 |
    (p & 0x80) >> 4 | (p & 0x200) >> 5 | (p & 0x800) >> 6 |
    (p & 0x2000) >> 7 | (p & 0x8000) >> 8 | (p & 0x20000) >> 9 |
    (p & 0x80000) >> 10 | (p & 0x200000) >> 11 | (p & 0x800000) >> 12 |
    (p & 0x2000000) >> 13 | (p & 0x8000000) >> 14 | (p & 0x20000000) >> 15
  return { x, y }
}

export function decode_id(id: number) {
  assert(id <= 0x7fffffff)
  let order = 0
  let l = (id >> 2) + 1
  while (l >= 4) {
    l >>= 2
    ++order
  }
  const index = id - (((1 << (2 * order)) - 1) << 2)
  return { order, index }
}

export function encode_id(order: number, index: number) {
  return 4 * ((1 << (2 * order)) - 1) + index
}

function assert(condition: boolean) {
  console.assert(condition)
  if (!condition) {
    debugger
  }
}

export function size2order(size: number) {
  let n = 0
  while (size > 1) {
    size >>= 1
    ++n
  }
  return n
}

const B = new Float32Array([
  81 / 4, -81 / 2, 99 / 4, -9 / 2, -81 / 2, 81, -99 / 2, 9, 99 / 4, -99 / 2, 121 / 4, -11 / 2, -9 / 2, 9, -11 / 2, 1,
  -243 / 4, 243 / 2, -297 / 4, 27 / 2, 405 / 4, -405 / 2, 495 / 4, -45 / 2, -81 / 2, 81, -99 / 2, 9, 0, 0, 0, 0,
  243 / 4, -243 / 2, 297 / 4, -27 / 2, -81, 162, -99, 18, 81 / 4, -81 / 2, 99 / 4, -9 / 2, 0, 0, 0, 0,
  -81 / 4, 81 / 2, -99 / 4, 9 / 2, 81 / 4, -81 / 2, 99 / 4, -9 / 2, -9 / 2, 9, -11 / 2, 1, 0, 0, 0, 0,
  -243 / 4, 405 / 4, -81 / 2, 0, 243 / 2, -405 / 2, 81, 0, -297 / 4, 495 / 4, -99 / 2, 0, 27 / 2, -45 / 2, 9, 0,
  729 / 4, -1215 / 4, 243 / 2, 0, -1215 / 4, 2025 / 4, -405 / 2, 0, 243 / 2, -405 / 2, 81, 0, 0, 0, 0, 0,
  -729 / 4, 1215 / 4, -243 / 2, 0, 243, -405, 162, 0, -243 / 4, 405 / 4, -81 / 2, 0, 0, 0, 0, 0,
  243 / 4, -405 / 4, 81 / 2, 0, -243 / 4, 405 / 4, -81 / 2, 0, 27 / 2, -45 / 2, 9, 0, 0, 0, 0, 0,
  243 / 4, -81, 81 / 4, 0, -243 / 2, 162, -81 / 2, 0, 297 / 4, -99, 99 / 4, 0, -27 / 2, 18, -9 / 2, 0,
  -729 / 4, 243, -243 / 4, 0, 1215 / 4, -405, 405 / 4, 0, -243 / 2, 162, -81 / 2, 0, 0, 0, 0, 0,
  729 / 4, -243, 243 / 4, 0, -243, 324, -81, 0, 243 / 4, -81, 81 / 4, 0, 0, 0, 0, 0,
  -243 / 4, 81, -81 / 4, 0, 243 / 4, -81, 81 / 4, 0, -27 / 2, 18, -9 / 2, 0, 0, 0, 0, 0,
  -81 / 4, 81 / 4, -9 / 2, 0, 81 / 2, -81 / 2, 9, 0, -99 / 4, 99 / 4, -11 / 2, 0, 9 / 2, -9 / 2, 1, 0,
  243 / 4, -243 / 4, 27 / 2, 0, -405 / 4, 405 / 4, -45 / 2, 0, 81 / 2, -81 / 2, 9, 0, 0, 0, 0, 0,
  -243 / 4, 243 / 4, -27 / 2, 0, 81, -81, 18, 0, -81 / 4, 81 / 4, -9 / 2, 0, 0, 0, 0, 0,
  81 / 4, -81 / 4, 9 / 2, 0, -81 / 4, 81 / 4, -9 / 2, 0, 9 / 2, -9 / 2, 1, 0, 0, 0, 0, 0])
