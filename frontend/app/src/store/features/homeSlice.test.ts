import { describe, expect, it } from "vitest"
import {
  hasExplicitDetectorSelection,
  parseDetectorName,
  readHighlightedCcds,
  writeHighlightedCcds,
} from "./homeSlice"


describe("highlight detector URL helpers", () => {
  it("reads a single detector query parameter", () => {
    const searchParams = new URLSearchParams("detector=0")

    expect(readHighlightedCcds(searchParams)).toEqual(["R01_S00"])
    expect(hasExplicitDetectorSelection(searchParams)).toBe(true)
  })

  it("reads the legacy detectors query parameter", () => {
    const searchParams = new URLSearchParams("detectors=R22_S00,R22_S01")

    expect(readHighlightedCcds(searchParams)).toEqual(["R22_S00", "R22_S01"])
  })

  it("writes a single highlighted ccd to detector", () => {
    const next = writeHighlightedCcds(new URLSearchParams("foo=bar"), ["R22_S00"])

    expect(next.toString()).toBe("foo=bar&detector=R22_S00")
  })

  it("writes multiple highlighted ccds to detectors", () => {
    const next = writeHighlightedCcds(new URLSearchParams("foo=bar"), ["R22_S00", "R22_S01"])

    expect(next.toString()).toBe("foo=bar&detectors=R22_S00%2CR22_S01")
  })

  it("parses detector ids into ccd names", () => {
    expect(parseDetectorName("0")).toBe("R01_S00")
  })
})
