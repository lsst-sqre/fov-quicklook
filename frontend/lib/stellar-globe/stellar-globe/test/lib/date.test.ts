// https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/cande/date2jd.cgi
// https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/cande/gst.cgi

import { describe, expect, it } from "vitest"
import { JulianDay, modifiedJulianDay, siderealTimeHour } from "~/utils/date"

describe('2022-09-30T11:07:10+09:00', () => {
  const date = new Date('2022-09-30T11:07:10+09:00')

  it('JulianDay', () => {
    expect(JulianDay(date)).toBeCloseTo(2459852.58831)
  })

  it('modifiedJulianDay', () => {
    expect(modifiedJulianDay(date)).toBeCloseTo(59852.08831)
  })

  it('siderealTime', () => {
    expect(siderealTimeHour(date)).toBeCloseTo(hmsToHour('2:42:25.159'))
  })
})


function hmsToHour(hms: string) {
  if (hms.startsWith('-')) {
    throw new Error(`Invalid HMS format: ${hms}`)
  }
  const [h, m, s] = hms.split(':').map(s => Number(s))
  return h + (m + s / 60) / 60
}
