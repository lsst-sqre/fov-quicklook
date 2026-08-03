import { describe, expect, it } from "vitest"
import { buildVisitListQuery, extractSearchDateFromVisitId, searchDateToDayObs } from "./visitSearch"

describe("visit search helpers", () => {
  it("converts a selected date to day_obs", () => {
    expect(searchDateToDayObs("2025-05-19")).toBe(20250519)
  })

  it("returns no day_obs for invalid input", () => {
    expect(searchDateToDayObs("2025051900437")).toBeUndefined()
    expect(searchDateToDayObs("")).toBeUndefined()
  })

  it("builds a date-only visit query", () => {
    expect(buildVisitListQuery("2025-05-19", "embargo:LSSTCam!-raw!-all:raw")).toEqual({
      repositoryName: "embargo",
      collection: "LSSTCam/raw/all",
      datasetType: "raw",
      where: "day_obs=20250519",
    })
  })

  it("does not build an exposure query from a direct exposure id", () => {
    expect(buildVisitListQuery("2025051900437", "embargo:LSSTCam!-raw!-all:raw")).toEqual({
      repositoryName: "embargo",
      collection: "LSSTCam/raw/all",
      datasetType: "raw",
    })
  })

  it("extracts a date input value from a visit id", () => {
    expect(extractSearchDateFromVisitId("embargo:LSSTCam!-raw!-all:raw:exposure=2025051900437")).toBe("2025-05-19")
  })
})
