import { describe, expect, it } from "vitest"
import {
  buildCalendarDayCells,
  buildVisitCountsByDate,
  dayObsToSearchDate,
  formatCalendarMonthLabel,
  getInitialCalendarMonth,
  getSelectedCalendarDate,
  getTodaySearchDate,
  shiftCalendarMonth,
} from "./visitCalendar"

describe("visit calendar helpers", () => {
  it("formats day_obs values as search dates", () => {
    expect(dayObsToSearchDate(20250519)).toBe("2025-05-19")
    expect(dayObsToSearchDate(123)).toBe("")
  })

  it("formats today's date", () => {
    expect(getTodaySearchDate(new Date(2025, 4, 19))).toBe("2025-05-19")
  })

  it("uses the selected visit month when opening the calendar", () => {
    expect(getInitialCalendarMonth("embargo:raw:2025051900437", new Date(2024, 0, 1))).toBe("2025-05")
  })

  it("falls back to today when there is no selected visit", () => {
    expect(getInitialCalendarMonth(undefined, new Date(2025, 3, 7))).toBe("2025-04")
  })

  it("prefers the manual search date for the selected day", () => {
    expect(getSelectedCalendarDate("2025-05-18", "embargo:raw:2025051900437")).toBe("2025-05-18")
  })

  it("falls back to the selected visit date for the selected day", () => {
    expect(getSelectedCalendarDate("", "embargo:raw:2025051900437")).toBe("2025-05-19")
  })

  it("can move across month boundaries", () => {
    expect(shiftCalendarMonth("2025-01", -1)).toBe("2024-12")
    expect(shiftCalendarMonth("2025-12", 1)).toBe("2026-01")
  })

  it("creates a six-week calendar grid", () => {
    const cells = buildCalendarDayCells("2025-05")

    expect(cells).toHaveLength(42)
    expect(cells[0]).toEqual({
      date: "2025-04-27",
      day: 27,
      inCurrentMonth: false,
    })
    expect(cells[4]).toEqual({
      date: "2025-05-01",
      day: 1,
      inCurrentMonth: true,
    })
  })

  it("counts visits by date within the visible month", () => {
    expect(buildVisitCountsByDate([
      { day_obs: 20250519, count: 2 },
      { day_obs: 20250520, count: 1 },
      { day_obs: 20250430, count: 9 },
    ], "2025-05")).toEqual({
      "2025-05-19": 2,
      "2025-05-20": 1,
    })
  })

  it("formats month labels for the modal header", () => {
    expect(formatCalendarMonthLabel("2025-05")).toBe("May 2025")
  })
})
