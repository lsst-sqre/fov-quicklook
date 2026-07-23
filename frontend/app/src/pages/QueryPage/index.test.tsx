import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { Provider } from "react-redux"
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { QueryPage } from "."
import { makeStore } from "../../store"
import { buildQueryPythonSnippet } from "./queryParams"

const { useListVisitsQuery } = vi.hoisted(() => ({
  useListVisitsQuery: vi.fn(),
}))
const { copyTextToClipboard } = vi.hoisted(() => ({
  copyTextToClipboard: vi.fn(),
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

vi.mock("../../utils/copyTextToClipboard", () => ({
  copyTextToClipboard,
}))

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
      collections_truncated: false,
      dataset_types: ["main_raw"],
      dataset_types_truncated: false,
      where_examples: datasetType === "main_raw"
        ? [{ label: "Latest exposure (42)", where: "exposure=42" }]
        : [],
    }
  }

  return {
    repositories: ["embargo", "main"],
    collections: collection?.includes("nightly")
      ? ["LSSTCam/runs/nightlyValidation"]
      : ["LSSTCam/raw/all", "LSSTCam/runs/nightlyValidation"],
    collections_truncated: collection?.includes("nightly") ?? false,
    dataset_types: datasetType === "prelim"
      ? ["preliminary_visit_image"]
      : ["raw", "calexp", "difference_image", "preliminary_visit_image"],
    dataset_types_truncated: false,
    where_examples: datasetType === "difference_image"
      ? [{ label: "Latest visit (7001)", where: "visit=7001" }]
      : datasetType === "raw"
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

const baseSystemInfo = {
  admin_page: false,
  context_menu_templates: [],
  max_object_storage_usage: 0,
  query_builder_input_mode: "combobox",
  butler_scopes: [
    {
      id: "main:main!-raw:main_raw",
      repository_name: "main",
      collection: "main/raw",
      dataset_type: "main_raw",
      display_name: "Main Raw",
      instrument: "LSSTCam",
    },
    {
      id: "embargo:LSSTCam!-raw!-all:raw",
      repository_name: "embargo",
      collection: "LSSTCam/raw/all",
      dataset_type: "raw",
      display_name: "Embargo Raw",
      instrument: "LSSTCam",
    },
    {
      id: "embargo:LSSTCam!-runs!-nightlyValidation:difference_image",
      repository_name: "embargo",
      collection: "LSSTCam/runs/nightlyValidation",
      dataset_type: "difference_image",
      display_name: "Embargo Difference Image",
      instrument: "LSSTCam",
    },
  ],
  datasets: [],
}

function renderQueryPage(initialEntries: string[], systemInfo = baseSystemInfo) {
  return render(
    <Provider store={makeStore(systemInfo as never)}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route element={<QueryRoute />} path="/query" />
        </Routes>
      </MemoryRouter>
    </Provider>,
  )
}

describe("QueryPage", () => {
  beforeEach(() => {
    sessionStorage.clear()
    useListVisitsQuery.mockReset()
    copyTextToClipboard.mockReset()
    useListVisitsQuery.mockReturnValue({
      data: [
        {
          id: "embargo:LSSTCam!-raw!-all:raw:exposure=2026012800342",
          display_id: "embargo:LSSTCam/raw/all:raw:exposure=2026012800342",
          scope_id: "embargo:LSSTCam!-raw!-all:raw",
          day_obs: 20260128,
          utc_start: "2026-01-28T03:42:00+00:00",
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
      if (urlText.includes("/api/visits/") && urlText.endsWith("/ccds")) {
        return jsonResponse(["R22_S11", "R22_S12"])
      }
      throw new Error(`Unexpected fetch: ${urlText}`)
    }))
  })

  afterEach(() => {
    cleanup()
    sessionStorage.clear()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("renders search results from the current query string", async () => {
    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })
    expect((screen.getByLabelText("Collection") as HTMLInputElement).value).toBe("LSSTCam/raw/all")
    expect((screen.getByLabelText("Dataset Type") as HTMLInputElement).value).toBe("raw")
    expect(useListVisitsQuery).toHaveBeenCalled()
    expect(screen.getByText("exposure=2026012800342")).toBeTruthy()
    expect(screen.getByText("UTC")).toBeTruthy()
    expect(screen.getByText("Visit").style.position).toBe("sticky")
    expect(screen.getByText("2026-01-28T03:42:00+00:00")).toBeTruthy()
    expect(screen.getByText("field-342")).toBeTruthy()
    expect(screen.queryByRole("button", { name: /Open by UUID/i })).toBeNull()
  })

  it("opens the header page for the first CCD", async () => {
    const openedWindow = {
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window
    const openSpy = vi.spyOn(window, "open").mockReturnValue(openedWindow)

    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"])

    const button = await screen.findByRole("button", { name: "Header" })
    expect(button.getAttribute("title")).toBe("Show the Header of the first CCD")

    fireEvent.click(button)

    await waitFor(() => {
      expect(openSpy).toHaveBeenCalledWith("", "_blank")
      expect(openedWindow.location.href).toBe(
        `http://example.test/header/${encodeURIComponent("embargo:LSSTCam!-raw!-all:raw:exposure=2026012800342")}/${encodeURIComponent("R22_S11")}`,
      )
    })
  })

  it("restores the last query from session storage when reopened", async () => {
    const savedQuery = new URLSearchParams({
      repository_name: "embargo",
      collection: "LSSTCam/raw/all",
      dataset_type: "raw",
      limit: "25",
    }).toString()
    const firstRender = renderQueryPage([`/query?${savedQuery}`])

    await waitFor(() => {
      expect(sessionStorage.getItem("fov-quicklook/queryPageSearch")).toBe(
        JSON.stringify(savedQuery),
      )
    })

    firstRender.unmount()
    useListVisitsQuery.mockClear()

    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })

    expect((screen.getByLabelText("Collection") as HTMLInputElement).value).toBe("LSSTCam/raw/all")
    expect((screen.getByLabelText("Dataset Type") as HTMLInputElement).value).toBe("raw")
    expect(screen.getByDisplayValue("25")).toBeTruthy()
    expect(screen.getByTestId("location-search").textContent).toBe("")
    const queryCall = useListVisitsQuery.mock.calls.find((call) => call[1]?.skip === false)
    expect(queryCall?.[0]).toEqual({
      repositoryName: "embargo",
      collection: "LSSTCam/raw/all",
      datasetType: "raw",
      limit: 25,
      reverse: undefined,
    })
  })

  it("preselects the first configured butler scope without navigating", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })
    expect((screen.getByLabelText("Collection") as HTMLInputElement).value).toBe("main/raw")
    expect((screen.getByLabelText("Dataset Type") as HTMLInputElement).value).toBe("main_raw")
    expect(screen.getByTestId("location-search").textContent).toBe("")
    const lastCall = useListVisitsQuery.mock.calls[useListVisitsQuery.mock.calls.length - 1]
    expect(lastCall?.[1]?.skip).toBe(true)
  })

  it("supports dynamic narrowing in combobox mode by default", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })

    fireEvent.change(screen.getByDisplayValue("main"), { target: { value: "embargo" } })
    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })
    fireEvent.change(screen.getByLabelText("Collection"), { target: { value: "LSSTCam/runs/nightlyValidation" } })
    fireEvent.change(screen.getByLabelText("Dataset Type"), { target: { value: "difference_image" } })
    await waitFor(() => {
      expect(screen.getByDisplayValue("difference_image")).toBeTruthy()
    })
    fireEvent.change(screen.getByDisplayValue("Select example"), { target: { value: "visit=7001" } })

    expect((screen.getByLabelText("Where") as HTMLInputElement).value).toBe("visit=7001")

    fireEvent.click(screen.getByRole("button", { name: "Search" }))

    await waitFor(() => {
      expect(screen.getByTestId("location-search").textContent).toContain("repository_name=embargo")
    })
  })

  it("shows a trailing ellipsis option for truncated collection results without selecting it", async () => {
    const { container } = renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })

    fireEvent.change(screen.getByDisplayValue("main"), { target: { value: "embargo" } })
    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })

    const collectionInput = screen.getByLabelText("Collection") as HTMLInputElement
    fireEvent.change(collectionInput, { target: { value: "nightly" } })

    await waitFor(() => {
      expect(container.querySelector('[role="listbox"]')?.textContent).toContain("...")
    })

    fireEvent.keyDown(collectionInput, { key: "Escape" })

    expect(collectionInput.value).toBe("nightly")
  })

  it("shows all collection options when the combobox input is empty", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })

    fireEvent.change(screen.getByDisplayValue("main"), { target: { value: "embargo" } })
    const collectionInput = screen.getByLabelText("Collection") as HTMLInputElement
    fireEvent.focus(collectionInput)

    await waitFor(() => {
      expect(screen.getByRole("listbox").textContent).toContain("LSSTCam/raw/all")
    })
    expect(screen.getByRole("listbox").textContent).toContain("LSSTCam/runs/nightlyValidation")
  })

  it("supports keyboard selection in the custom combobox", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })

    fireEvent.change(screen.getByDisplayValue("main"), { target: { value: "embargo" } })
    const collectionInput = screen.getByLabelText("Collection") as HTMLInputElement
    fireEvent.change(collectionInput, { target: { value: "nightly" } })

    await waitFor(() => {
      expect(screen.getByRole("listbox").textContent).toContain("LSSTCam/runs/nightlyValidation")
    })

    fireEvent.keyDown(collectionInput, { key: "ArrowDown" })
    fireEvent.keyDown(collectionInput, { key: "Enter" })

    expect(collectionInput.value).toBe("LSSTCam/runs/nightlyValidation")
  })

  it("submits the default query without adding where=null", async () => {
    renderQueryPage(["/query"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("main")).toBeTruthy()
    })

    fireEvent.click(screen.getByRole("button", { name: "Search" }))

    await waitFor(() => {
      expect(screen.getByTestId("location-search").textContent).toContain("repository_name=main")
    })
    expect(screen.getByTestId("location-search").textContent).not.toContain("where=null")
    const queryCall = useListVisitsQuery.mock.calls.find((call) => call[0]?.repositoryName === "main" && call[1]?.skip === false)
    expect(queryCall?.[0]).toEqual({
      repositoryName: "main",
      collection: "main/raw",
      datasetType: "main_raw",
      where: "",
      orderBy: "day_obs",
      limit: 100,
      reverse: undefined,
    })
  })

  it("copies runnable python code for the current query string", async () => {
    renderQueryPage(["/query?repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"])

    await waitFor(() => {
      expect(screen.getByDisplayValue("embargo")).toBeTruthy()
    })

    fireEvent.click(screen.getByRole("button", { name: "Copy Python" }))

    expect(copyTextToClipboard).toHaveBeenCalledTimes(1)
    expect(copyTextToClipboard).toHaveBeenCalledWith(
      buildQueryPythonSnippet("repository_name=embargo&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=100"),
    )
  })

  it("queries across all collections when collection is empty and shows a collection column", async () => {
    useListVisitsQuery.mockReturnValue({
      data: [
        {
          id: "embargo:LSSTCam!-raw!-all:raw:exposure=2026012800342",
          display_id: "embargo:LSSTCam/raw/all:raw:exposure=2026012800342",
          scope_id: "embargo:LSSTCam!-raw!-all:raw",
          day_obs: 20260128,
          utc_start: "2026-01-28T03:42:00+00:00",
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

    renderQueryPage(["/query?repository_name=embargo&dataset_type=raw&limit=100"])

    await waitFor(() => {
      expect(useListVisitsQuery).toHaveBeenCalled()
    })

    expect(screen.getAllByText("Collection").length).toBeGreaterThan(1)
    expect(screen.getByText("LSSTCam/raw/all")).toBeTruthy()
    const queryCall = useListVisitsQuery.mock.calls.find((call) => call[1]?.skip === false)
    expect(queryCall?.[0]).toEqual({
      repositoryName: "embargo",
      datasetType: "raw",
      limit: 100,
      reverse: undefined,
    })
  })
})
