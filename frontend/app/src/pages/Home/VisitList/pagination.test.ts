import { describe, expect, it } from "vitest"
import {
  buildVisitListPageQuery,
  getVisibleVisitEntries,
  hasNextVisitPage,
  shouldShowVisitPagination,
  VISIT_LIST_PAGE_SIZE,
} from "./pagination"

describe("visit list pagination helpers", () => {
  it("builds a paged query from the current filters", () => {
    expect(buildVisitListPageQuery({
      dayObs: 20250519,
      dataType: "raw",
      repositoryName: "embargo",
    }, 2)).toEqual({
      dayObs: 20250519,
      dataType: "raw",
      repositoryName: "embargo",
      limit: VISIT_LIST_PAGE_SIZE + 1,
      offset: VISIT_LIST_PAGE_SIZE * 2,
    })
  })

  it("shows only the entries for the current page", () => {
    const entries = Array.from({ length: VISIT_LIST_PAGE_SIZE + 2 }, (_, index) => ({
      id: `embargo:raw:${index}`,
      day_obs: 20250519,
      physical_filter: "r",
      obs_id: `obs-${index}`,
      exposure_time: 30,
      science_program: "program",
      observation_type: "science",
      observation_reason: "survey",
      target_name: `field-${index}`,
    }))

    expect(getVisibleVisitEntries(entries)).toHaveLength(VISIT_LIST_PAGE_SIZE)
    expect(hasNextVisitPage(entries)).toBe(true)
  })

  it("hides navigation when there is only one page", () => {
    expect(shouldShowVisitPagination(0, false)).toBe(false)
    expect(hasNextVisitPage(undefined)).toBe(false)
  })
})
