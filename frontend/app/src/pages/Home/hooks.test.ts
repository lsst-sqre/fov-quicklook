import { describe, expect, it } from "vitest"
import { CcdMetadata } from "../../store/api/openapi"
import { ccdSkyCoordFromFocalPlaneCoord } from "./hooks"


describe("ccdSkyCoordFromFocalPlaneCoord", () => {
  it("maps focal-plane coordinates through the focused CCD WCS", () => {
    const focusedCcd: Pick<CcdMetadata, "bbox" | "wcs"> = {
      bbox: {
        minx: 100,
        miny: 200,
        maxx: 199,
        maxy: 299,
      },
      wcs: {
        NAXIS1: 100,
        NAXIS2: 100,
        CTYPE1: "RA---TAN",
        CTYPE2: "DEC--TAN",
        CRVAL1: 10,
        CRVAL2: 20,
        CRPIX1: 1,
        CRPIX2: 1,
        CD1_1: -0.0001,
        CD1_2: 0,
        CD2_1: 0,
        CD2_2: 0.0001,
      },
    }

    const skyCoord = ccdSkyCoordFromFocalPlaneCoord(focusedCcd, [100.5, 200.5])

    expect(skyCoord?.a.deg).toBeCloseTo(10, 5)
    expect(skyCoord?.d.deg).toBeCloseTo(20, 5)
  })

  it("returns undefined when the focused CCD has no WCS", () => {
    const focusedCcd: Pick<CcdMetadata, "bbox" | "wcs"> = {
      bbox: {
        minx: 100,
        miny: 200,
        maxx: 199,
        maxy: 299,
      },
      wcs: null,
    }

    expect(ccdSkyCoordFromFocalPlaneCoord(focusedCcd, [100.5, 200.5])).toBeUndefined()
  })
})
