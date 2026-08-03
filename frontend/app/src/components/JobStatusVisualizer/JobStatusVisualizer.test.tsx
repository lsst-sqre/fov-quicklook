import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { JobStatusVisualizer } from "./JobStatusVisualizer"

describe("JobStatusVisualizer", () => {
  it("shows the target in the tile generation heading", () => {
    render(
      <MemoryRouter>
        <JobStatusVisualizer
          status={{
            job: {
              visit: "reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910001",
            },
            generate_single_fits_tiles: {
              R22_S00: {
                total: 10,
                count: 5,
              },
            },
          }}
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Generating Tiles for reviewapp-ci:LSSTCam/raw/all:raw:exposure=910001",
      }),
    ).toBeTruthy()
  })
})
