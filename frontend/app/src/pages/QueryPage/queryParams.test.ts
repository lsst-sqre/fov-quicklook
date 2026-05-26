import { describe, expect, it } from "vitest"
import { buildDefaultQueryInput, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

describe("query params helpers", () => {
  it("normalizes an optional /query prefix", () => {
    expect(normalizeQueryInput("/query?data_type=raw&repository_name=embargo")).toBe("data_type=raw&repository_name=embargo")
    expect(normalizeQueryInput("?data_type=raw")).toBe("data_type=raw")
  })

  it("builds list visit arguments from the URL search params", () => {
    const result = buildVisitListArgs(
      new URLSearchParams("data_type=raw&repository_name=embargo&limit=2&offset=1000&day_obs=20260128&order=-day_obs,-exposure&ra_deg=53.6&dec_deg=-32.7&radius_deg=1.5"),
    )

    expect(result).toEqual({
      args: {
        dataType: "raw",
        repositoryName: "embargo",
        limit: 2,
        offset: 1000,
        dayObs: 20260128,
        order: "-day_obs,-exposure",
        raDeg: 53.6,
        decDeg: -32.7,
        radiusDeg: 1.5,
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

  it("reports incomplete spatial parameters", () => {
    expect(buildVisitListArgs(new URLSearchParams("data_type=raw&repository_name=embargo&ra_deg=53.6&radius_deg=1.5"))).toEqual({
      args: null,
      error: "ra_deg, dec_deg, and radius_deg must be specified together.",
    })
  })

  it("builds a default query string from the current datasource", () => {
    expect(buildDefaultQueryInput("main:raw")).toBe("data_type=raw&repository_name=main&limit=100")
    expect(buildDefaultQueryInput("embargo:difference_image", 5)).toBe("data_type=difference_image&repository_name=embargo&limit=5")
  })
})
