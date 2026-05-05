import { deg2rad } from "~/lib/angle"


export function JulianDay(date: Date) {
  return (Number(date) / 86400000) + 2440587.5
}


export function modifiedJulianDay(date: Date) {
  return JulianDay(date) - 2400000.5
}


export function siderealTimeHour(date: Date) {
  const jd = JulianDay(date)
  const tjd = jd - 2_440_000.5 // truncated Julian Day (NASA)
  let t = 0.671_262 + 1.002_737_909_4 * tjd
  t = t >= 0 ? t % 1 : 1 - (-t % 1)
  return 24 * t
}


export function siderealTimeRadian(date: Date) {
  const h = siderealTimeHour(date)
  return deg2rad(h * 15)
}


type EarthLocation = {
  lat: number
  lon: number
}


export function zenithSkyCoord({ when, where, zp }: { when: Date, where: EarthLocation, zp?: number }) {
  const ra = siderealTimeRadian(when) + deg2rad(where.lon)
  const dec = deg2rad(where.lat)
  return {
    za: ra,
    zd: dec,
    zp: zp ?? 0,
  }
}
