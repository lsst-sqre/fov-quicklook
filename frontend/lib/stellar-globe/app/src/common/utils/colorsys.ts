import { V4 } from "@stellar-globe/stellar-globe"

export function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  h *= 360
  let r = -1
  let g = -1
  let b = -1
  const i = Math.floor(h / 60)
  const f = h / 60 - i
  const p = v * (1 - s)
  const q = v * (1 - s * f)
  const t = v * (1 - s * (1 - f))

  switch (i % 6) {
    case 0: r = v, g = t, b = p; break
    case 1: r = q, g = v, b = p; break
    case 2: r = p, g = v, b = t; break
    case 3: r = p, g = q, b = v; break
    case 4: r = t, g = p, b = v; break
    case 5: r = v, g = p, b = q; break
  }

  return [r, g, b]
}


export function colorSeries(
  index: number,
  options: { saturation?: number, alpha?: number } = {},
): V4 {
  return [...hsvToRgb(5 * (index + 4) / 12, options.saturation ?? 0.5, 1), options.alpha ?? 1]
}
