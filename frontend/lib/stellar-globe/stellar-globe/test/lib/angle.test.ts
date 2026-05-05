import { Angle, SkyCoord } from '~/lib/angle'
import { it, describe, expect } from 'vitest'



describe('Angle', () => {
  it('.fromRad(PI/4) == 45 degree', () => {
    expect(Angle.fromRad(Math.PI / 4).deg).toBeCloseTo(45)
  })
  it('.fromAmin(60) == 1 deg', () => {
    expect(Angle.fromAmin(60).deg).toBeCloseTo(1)
  })
  it('.fromAsec(1) == 1 / 3600 degree', () => {
    expect(Angle.fromAsec(1).deg).toBeCloseTo(1 / 3600)
  })
  it('.fromDeg(1) == 60 arcmin', () => {
    expect(Angle.fromDeg(1).amin).toBeCloseTo(60)
  })
  it('.fromDeg(1) == 3600 arcsec)', () => {
    expect(Angle.fromDeg(1).asec).toBeCloseTo(3600)
  })
})

describe('SkyCoord#xyz', () => {
  it('returns unit vector', () => {
    expect(SkyCoord.fromDeg(0, 0).xyz).toBeArrayCloseTo([1, 0, 0])
    expect(SkyCoord.fromDeg(90, 0).xyz).toBeArrayCloseTo([0, 1, 0])
    expect(SkyCoord.fromDeg(90, 90).xyz).toBeArrayCloseTo([0, 0, 1])
    expect(SkyCoord.fromDeg(0, -45).xyz).toBeArrayCloseTo([Math.SQRT1_2, 0, -Math.SQRT1_2])
    expect(SkyCoord.fromDeg(-45, -45).xyz).toBeArrayCloseTo([1 / 2, - 1 / 2, -Math.SQRT1_2])
  })
})

describe('SkyCoord.fromXyz', () => {
  function check(coord: SkyCoord, a: Angle, d: Angle) {
    return expect([coord.a.rad, coord.d.rad]).toBeArrayCloseTo([a.rad, d.rad])
  }

  it('returns SkyCoord', () => {
    check(SkyCoord.fromXyz([1, 0, 0]), Angle.fromDeg(0), Angle.fromDeg(0))
    check(SkyCoord.fromXyz([0, 1, 0]), Angle.fromDeg(90), Angle.fromDeg(0))
    check(SkyCoord.fromXyz([0, 0, 1]), Angle.fromDeg(0), Angle.fromDeg(90))
    check(SkyCoord.fromXyz([Math.SQRT1_2, 0, -Math.SQRT1_2]), Angle.fromDeg(0), Angle.fromDeg(-45))
    check(SkyCoord.fromXyz([1 / 2, -1 / 2, -Math.SQRT1_2]), Angle.fromDeg(315), Angle.fromDeg(-45))
  })
})


describe('SkyCoord.parse', () => {
  it('parses simple coord string', () => {
    const coord = SkyCoord.parse(`29 41`)
    expect(coord.a.deg).toBeCloseTo(29)
    expect(coord.d.deg).toBeCloseTo(41)
  })

  it('parses complex coord string such as `(RA, α) 09h 55m 33.17306s (Dec, δ) +69° 03′ 55.0610″`', () => {
    const eq = SkyCoord.parse(`(RA, α) 09h 55m 33.17306s (Dec, δ) +69° 03′ 55.0610″`)
    const { a, d } = eq.toString()
    expect(a).toBe('09:55:33.1731')
    expect(d).toBe('+69:03:55.0610')
  })

  it('parses coord string includings "floating-point expression" such as `173.92488824340327 7.471561224924194e-07`', () => {
    const s = `173.92488824340327 7.471561224924194e-07`
    const { a, d } = SkyCoord.parse(s)
    expect(a.deg).toBeCloseTo(173.92488824340327)
    expect(d.deg).toBeCloseTo(7.471561224924194e-07)
  })
})