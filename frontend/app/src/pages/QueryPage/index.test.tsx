import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes, useLocation, useParams } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { QueryPage } from "."

const { useListVisitsQuery } = vi.hoisted(() => ({
  useListVisitsQuery: vi.fn(),
}))

vi.mock("../../env", () => ({
  env: {
    baseUrl: "http://example.test",
  },
}))

vi.mock("../../store/api/openapi", () => ({
  useListVisitsQuery,
}))

function QueryRoute() {
  const location = useLocation()
  return (
    <>
      <QueryPage />
      <div data-testid="location-search">{location.search}</div>
    </>
  )
}

function VisitRoute() {
  const { visitId } = useParams()
  return <div>{visitId}</div>
}

describe("QueryPage", () => {
  beforeEach(() => {
    useListVisitsQuery.mockReset()
    useListVisitsQuery.mockReturnValue({
      data: [
        {
          id: "embargo:raw:2026012800342",
          day_obs: 20260128,
          physical_filter: "r_57",
          obs_id: "obs-342",
          exposure_time: 30,
          science_program: "nightly",
          observation_type: "science",
          observation_reason: "survey",
          target_name: "field-342",
        },
      ],
      error: undefined,
      isFetching: false,
      isLoading: false,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders search results from the current query string", () => {
    render(
      <MemoryRouter initialEntries={["/query?data_type=raw&repository_name=embargo&limit=2"]}>
        <Routes>
          <Route element={<QueryRoute />} path="/query" />
        </Routes>
      </MemoryRouter>,
    )

    expect(useListVisitsQuery).toHaveBeenCalled()
    expect(screen.getByDisplayValue("data_type=raw&repository_name=embargo&limit=2")).toBeTruthy()
    expect(screen.getByText("embargo:raw:2026012800342")).toBeTruthy()
    expect(screen.getByText("field-342")).toBeTruthy()
  })

  it("re-runs the query when the input loses focus", async () => {
    render(
      <MemoryRouter initialEntries={["/query?data_type=raw&repository_name=embargo"]}>
        <Routes>
          <Route element={<QueryRoute />} path="/query" />
        </Routes>
      </MemoryRouter>,
    )

    const input = screen.getByLabelText("Query string")
    fireEvent.change(input, { target: { value: "data_type=raw&repository_name=main&limit=2" } })
    fireEvent.blur(input)

    await waitFor(() => {
      expect(screen.getByTestId("location-search").textContent).toBe("?data_type=raw&repository_name=main&limit=2")
    })
  })

  it("opens the selected visit via by_uuid", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ uuid: "uuid-1" }),
    } as Response)

    render(
      <MemoryRouter initialEntries={["/query?data_type=raw&repository_name=embargo&limit=2"]}>
        <Routes>
          <Route element={<QueryRoute />} path="/query" />
          <Route element={<VisitRoute />} path="/visits/:visitId" />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole("button", { name: "Open embargo:raw:2026012800342 by UUID" }))

    expect(await screen.findByText("embargo:by_uuid:uuid-1")).toBeTruthy()
  })
})
