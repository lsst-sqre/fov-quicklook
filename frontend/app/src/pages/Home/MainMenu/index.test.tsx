import { fireEvent, render, screen } from "@testing-library/react"
import { Provider } from "react-redux"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { MainMenu } from "."
import { makeStore } from "../../../store"

const navigateMock = vi.hoisted(() => vi.fn())

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock("../useHomeActions", () => ({
  useHomeActions: () => ({
    lineProfilerEnabled: false,
    recenter: vi.fn(),
    rotateClockwise: vi.fn(),
    toggleLineProfiler: vi.fn(),
  }),
}))

vi.mock("../../../components/MaterialSymbol", () => ({
  MaterialSymbol: ({ symbol }: { symbol: string }) => <span>{symbol}</span>,
}))

const systemInfo = {
  admin_page: false,
  context_menu_templates: [],
  max_object_storage_usage: 0,
  butler_scopes: [
    {
      id: "embargo:LSSTCam!-raw!-all:raw",
      repository_name: "embargo",
      collection: "LSSTCam/raw/all",
      dataset_type: "raw",
      display_name: "Embargo Raw",
      instrument: "LSSTCam",
    },
  ],
  datasets: [],
}

describe("MainMenu", () => {
  beforeEach(() => {
    navigateMock.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it("does not duplicate the Data Query link in the menu", () => {
    render(
      <Provider store={makeStore(systemInfo as never)}>
        <MainMenu />
      </Provider>,
    )

    fireEvent.click(screen.getByRole("button"))
    expect(screen.queryByRole("menuitem", { name: "Data Query" })).toBeNull()
    expect(navigateMock).not.toHaveBeenCalled()
  })
})
