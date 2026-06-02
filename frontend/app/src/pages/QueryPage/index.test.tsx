import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { Provider } from "react-redux"
import { MemoryRouter, Route, Routes, useLocation, useParams } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { QueryPage } from "."
import { makeStore } from "../../store"

const { useListVisitsQuery } = vi.hoisted(() => ({
  useListVisitsQuery: vi.fn(),
}))

vi.mock("../../env", () => ({
  env: {
    baseUrl: "http://example.test",
  },
}))

vi.mock("../../store/api/openapi", async () => {
  const actual = await vi.importActual<typeof import("../../store/api/openapi")>("../../store/api/openapi")
  return {
    ...actual,
    useListVisitsQuery,
  }
})

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

const systemInfo = {
  admin_page: false,
  context_menu_templates: [],
  max_object_storage_usage: 0,
  butler_scopes: [
    {
      id: "embargo:LSSTCam!-raw!-all:raw",
      dataset_type: "raw",
      display_name: "Embargo Raw",
      collection: "LSSTCam/raw/all",
      repository_name: "embargo",
      instrument: "LSSTCam",
    },
    {
      id: "main:main!-raw:main_raw",
      dataset_type: "main_raw",
      display_name: "Main Raw",
      collection: "main/raw",
      repository_name: "main",
      instrument: "LSSTCam",
    },
  ],
  datasets: [],
}

function renderQueryPage(initialEntries: string[]) {
  return render(
    <Provider store={makeStore(systemInfo as never)}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route element={<QueryRoute />} path="/query" />
          <Route element={<VisitRoute />} path="/visits/:visitId" />
        </Routes>
      </MemoryRouter>
    </Provider>,
  )
}

describe("QueryPage", () => {
  beforeEach(() => {
    useListVisitsQuery.mockReset()
    useListVisitsQuery.mockReturnValue({
      data: [
        {
          id: "embargo:LSSTCam!-raw!-all:raw:exposure=2026012800342",
          display_id: "embargo:LSSTCam/raw/all:raw:exposure=2026012800342",
          scope_id: "embargo:LSSTCam!-raw!-all:raw",
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
    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=2"])

    expect(useListVisitsQuery).toHaveBeenCalled()
    expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    expect(screen.getByText("embargo:LSSTCam/raw/all:raw:exposure=2026012800342")).toBeTruthy()
    expect(screen.getByText("field-342")).toBeTruthy()
  })

  it("uses the current datasource as the default query when /query has no search params", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByTestId("location-search").textContent).toBe("?repository_name=embargo&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=2")
    })
  })

  it("re-runs the query when the form is submitted", async () => {
    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw"])

    fireEvent.change(screen.getByDisplayValue("embargo"), { target: { value: "main" } })
    fireEvent.click(screen.getByRole("button", { name: "Search" }))

    await waitFor(() => {
      expect(screen.getByTestId("location-search").textContent).toContain("repository_name=main")
    })
  })

  it("opens the selected visit via by_uuid", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ uuid: "uuid-1" }),
    } as Response)

    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=2"])

    fireEvent.click(screen.getByRole("button", { name: "Open embargo:LSSTCam/raw/all:raw:exposure=2026012800342 by UUID" }))

    expect(await screen.findByText("embargo:by_uuid:uuid-1")).toBeTruthy()
  })
})
