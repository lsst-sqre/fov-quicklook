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
    expect(buildVisitListQuery("2025-05-19", "raw", "embargo")).toEqual({
      dayObs: 20250519,
      dataType: "raw",
      repositoryName: "embargo",
    })
  })

  it("does not build an exposure query from a direct exposure id", () => {
    expect(buildVisitListQuery("2025051900437", "raw", "embargo")).toEqual({
      dataType: "raw",
      repositoryName: "embargo",
    })
  })

  it("extracts a date input value from a visit id", () => {
    expect(extractSearchDateFromVisitId("embargo:raw:2025051900437")).toBe("2025-05-19")
  })
})
