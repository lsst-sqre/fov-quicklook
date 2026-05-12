import { describe, expect, it } from "vitest"
import { buildByUuidVisitName, buildDefaultQueryInput, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

describe("query params helpers", () => {
  it("normalizes an optional /query prefix", () => {
    expect(normalizeQueryInput("/query?data_type=raw&repository_name=embargo")).toBe("data_type=raw&repository_name=embargo")
    expect(normalizeQueryInput("?data_type=raw")).toBe("data_type=raw")
  })

  it("builds list visit arguments from the URL search params", () => {
    const result = buildVisitListArgs(new URLSearchParams("data_type=raw&repository_name=embargo&limit=2&day_obs=20260128"))

    expect(result).toEqual({
      args: {
        dataType: "raw",
        repositoryName: "embargo",
        limit: 2,
        dayObs: 20260128,
      },
      error: null,
    })
  })

  it("reports invalid integer parameters", () => {
    expect(buildVisitListArgs(new URLSearchParams("data_type=raw&repository_name=embargo&limit=two"))).toEqual({
      args: null,
      error: "limit must be an integer.",
    })
  })

  it("builds a by_uuid visit name", () => {
    expect(buildByUuidVisitName("embargo:difference_image:7001", "uuid-1")).toBe("embargo:by_uuid:uuid-1")
  })

  it("builds a default query string from the current datasource", () => {
    expect(buildDefaultQueryInput("main:raw")).toBe("data_type=raw&repository_name=main&limit=2")
    expect(buildDefaultQueryInput("embargo:difference_image", 5)).toBe("data_type=difference_image&repository_name=embargo&limit=5")
  })
})
