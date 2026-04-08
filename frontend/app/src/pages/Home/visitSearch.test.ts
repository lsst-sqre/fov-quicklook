import { describe, expect, it } from "vitest"
import {
  buildCalendarDayCounts,
  buildMonthDayCounts,
  buildVisitListQuery,
  buildVisitMonthlyCountsQuery,
  dayObsToSearchDate,
  extractSearchDateFromVisitId,
  getCurrentYearMonth,
  searchDateToDayObs,
} from "./visitSearch"

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

  it("formats day_obs back to a date input value", () => {
    expect(dayObsToSearchDate(20250519)).toBe("2025-05-19")
  })

  it("builds a monthly counts query", () => {
    expect(buildVisitMonthlyCountsQuery(2025, 5, "raw", "embargo")).toEqual({
      year: 2025,
      month: 5,
      dataType: "raw",
      repositoryName: "embargo",
    })
  })

  it("expands sparse daily counts to the full month", () => {
    const dayCounts = buildMonthDayCounts(2025, 2, [{ day_obs: 20250214, count: 3 }])

    expect(dayCounts).toHaveLength(28)
    expect(dayCounts[0]).toEqual({ day: 1, day_obs: 20250201, count: 0 })
    expect(dayCounts[13]).toEqual({ day: 14, day_obs: 20250214, count: 3 })
  })

  it("pads calendar rows so the first week starts on Sunday", () => {
    const calendarDayCounts = buildCalendarDayCounts(2025, 6, [{ day_obs: 20250601, count: 5 }])

    expect(calendarDayCounts[0]).toEqual({ day: 1, day_obs: 20250601, count: 5 })
    expect(calendarDayCounts).toHaveLength(35)
  })

  it("uses the provided date to compute the default year and month", () => {
    expect(getCurrentYearMonth(new Date(2025, 4, 19))).toEqual({ year: 2025, month: 5 })
  })
})
