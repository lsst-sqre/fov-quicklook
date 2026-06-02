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

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    json: async () => payload,
  } as Response
}

function buildOptions(urlText: string) {
  const url = new URL(urlText)
  const repositoryName = url.searchParams.get("repository_name")
  const collection = url.searchParams.get("collection")
  const datasetType = url.searchParams.get("dataset_type")

  if (repositoryName === "main") {
    return {
      repositories: ["embargo", "main"],
      collections: ["main/raw"],
      dataset_types: ["main_raw"],
      where_examples: datasetType === "main_raw"
        ? [{ label: "Latest exposure (42)", where: "exposure=42" }]
        : [],
    }
  }

  return {
    repositories: ["embargo", "main"],
    collections: ["LSSTCam/raw/all", "LSSTCam/runs/nightlyValidation"],
    dataset_types: collection === "LSSTCam/runs/nightlyValidation"
      ? ["difference_image", "preliminary_visit_image"]
      : ["raw", "calexp"],
    where_examples: datasetType === "raw"
      ? [{ label: "Latest day_obs (20260128)", where: "day_obs=20260128" }]
      : [],
  }
}

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
  butler_scopes: [],
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
    vi.stubGlobal("fetch", vi.fn(async (input: string | URL) => {
      const urlText = String(input)
      if (urlText.includes("/api/visits/query_builder_options")) {
        return jsonResponse(buildOptions(urlText))
      }
      if (urlText.includes("/representative_uuid")) {
        return jsonResponse({ uuid: "uuid-1" })
      }
      throw new Error(`Unexpected fetch: ${urlText}`)
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("renders search results from the current query string", async () => {
    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("repository_name=embargo&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=100")).toBeTruthy()
    })
    expect(useListVisitsQuery).toHaveBeenCalled()
    expect(screen.getByText("embargo:LSSTCam/raw/all:raw:exposure=2026012800342")).toBeTruthy()
    expect(screen.getByText("field-342")).toBeTruthy()
  })

  it("keeps /query empty until the user submits a query", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })
    expect((screen.getByLabelText("Query string") as HTMLInputElement).value).toBe("")
    expect(screen.getByTestId("location-search").textContent).toBe("")
    expect(useListVisitsQuery.mock.calls.at(-1)?.[1]?.skip).toBe(true)
  })

  it("lets the helper controls build the query string and where example", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })

    fireEvent.change(screen.getByDisplayValue("embargo"), { target: { value: "main" } })
    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })
    await waitFor(() => {
      expect(screen.getByDisplayValue("main_raw")).toBeTruthy()
    })
    fireEvent.change(screen.getByDisplayValue("Select example"), { target: { value: "exposure=42" } })

    expect(screen.getByDisplayValue("repository_name=main&collection=main%2Fraw&dataset_type=main_raw&order_by=day_obs&limit=100&where=exposure%3D42")).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: "Search" }))

    await waitFor(() => {
      expect(screen.getByTestId("location-search").textContent).toContain("repository_name=main")
    })
  })

  it("opens the selected visit via by_uuid", async () => {
    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"])

    fireEvent.click(screen.getByRole("button", { name: "Open embargo:LSSTCam/raw/all:raw:exposure=2026012800342 by UUID" }))

    expect(await screen.findByText("embargo:by_uuid:uuid-1")).toBeTruthy()
  })
})
