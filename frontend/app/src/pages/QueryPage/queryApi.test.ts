import { describe, expect, it } from "vitest"
import {
  buildButlerDatasetTypesApiUrl,
  buildButlerDimensionsApiUrl,
  buildButlerQueryApiUrl,
  formatQueryCellValue,
} from "./queryApi"


describe("butler query helpers", () => {
  it("builds the query API URL from current search params", () => {
    const searchParams = new URLSearchParams({ data_type: "raw", day_obs: "20260503", limit: "10" })

    expect(buildButlerQueryApiUrl("/fov-quicklook", searchParams))
      .toBe("/fov-quicklook/api/butler/query?data_type=raw&day_obs=20260503&limit=10")
  })

  it("builds the dataset types API URL with an optional repository filter", () => {
    expect(buildButlerDatasetTypesApiUrl("/fov-quicklook")).toBe("/fov-quicklook/api/butler/dataset_types")
    expect(buildButlerDatasetTypesApiUrl("/fov-quicklook", "embargo"))
      .toBe("/fov-quicklook/api/butler/dataset_types?repository_name=embargo")
  })

  it("builds the dimensions API URL", () => {
    expect(buildButlerDimensionsApiUrl("/fov-quicklook", "raw", "embargo"))
      .toBe("/fov-quicklook/api/butler/dataset_types/raw/dimensions?repository_name=embargo")
  })

  it("formats scalar and structured cell values", () => {
    expect(formatQueryCellValue("g")).toBe("g")
    expect(formatQueryCellValue(42)).toBe("42")
    expect(formatQueryCellValue({ detector: 12 })).toBe('{"detector":12}')
    expect(formatQueryCellValue(undefined)).toBe("")
  })
})
