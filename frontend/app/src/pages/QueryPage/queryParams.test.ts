import { describe, expect, it } from "vitest"
import { buildByUuidVisitName, buildDefaultQueryInput, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

describe("query params helpers", () => {
  it("normalizes an optional /query prefix", () => {
    expect(normalizeQueryInput("/query?data_type=raw&repository_name=embargo")).toBe("data_type=raw&repository_name=embargo")
    expect(normalizeQueryInput("?data_type=raw")).toBe("data_type=raw")
  })

  it("builds list visit arguments from the URL search params", () => {
    const result = buildVisitListArgs(new URLSearchParams("repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=2&offset=1000&where=day_obs=20260128"))

    expect(result).toEqual({
      args: {
        repositoryName: "embargo",
        collection: "LSSTCam/raw/all",
        datasetType: "raw",
        limit: 2,
        offset: 1000,
        where: "day_obs=20260128",
        reverse: undefined,
      },
      error: null,
    })
  })

  it("omits missing optional query params from the visit args", () => {
    const result = buildVisitListArgs(new URLSearchParams("repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"))

    expect(result).toEqual({
      args: {
        repositoryName: "embargo",
        collection: "LSSTCam/raw/all",
        datasetType: "raw",
        limit: 100,
        reverse: undefined,
      },
      error: null,
    })
  })

  it("reports invalid integer parameters", () => {
    expect(buildVisitListArgs(new URLSearchParams("repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=two"))).toEqual({
      args: null,
      error: "limit must be an integer.",
    })
  })

  it("builds a by_uuid visit name", () => {
    expect(buildByUuidVisitName("embargo:LSSTCam!-runs!-nightlyValidation:difference_image:visit=7001", "uuid-1")).toBe("embargo:by_uuid:uuid-1")
  })

  it("builds a default query string from the current datasource", () => {
    expect(buildDefaultQueryInput("main:LSSTCam!-raw!-all:raw")).toBe("repository_name=main&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=100")
    expect(buildDefaultQueryInput("embargo:LSSTCam!-runs!-nightlyValidation:difference_image", 5)).toBe("repository_name=embargo&collection=LSSTCam%2Fruns%2FnightlyValidation&dataset_type=difference_image&limit=5")
  })
})
