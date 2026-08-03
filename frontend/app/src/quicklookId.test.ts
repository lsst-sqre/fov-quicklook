import { describe, expect, it } from "vitest"
import { formatVisitIdForDisplay } from "./quicklookId"

describe("quicklookId display helpers", () => {
  it("renders canonical collection names for escaped visit ids", () => {
    expect(formatVisitIdForDisplay("embargo:LSSTCam!-raw!-all:raw:exposure=2026012800342")).toBe(
      "embargo:LSSTCam/raw/all:raw:exposure=2026012800342",
    )
  })
})
