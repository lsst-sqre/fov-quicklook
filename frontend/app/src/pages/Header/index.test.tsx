import { fireEvent, render, screen } from "@testing-library/react"
import { Provider } from "react-redux"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { Header } from "."
import { makeStore } from "../../store"

const navigateMock = vi.hoisted(() => vi.fn())

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock("../../components/MaterialSymbol", () => ({
  MaterialSymbol: ({ symbol }: { symbol: string }) => <span>{symbol}</span>,
}))

vi.mock("../../hooks/useAdminPageEnabled", () => ({
  useAdminPageEnabled: () => false,
}))

const systemInfo = {
  admin_page: false,
  context_menu_templates: [],
  max_object_storage_usage: 0,
  butler_scopes: [],
  datasets: [],
}

describe("Header", () => {
  beforeEach(() => {
    navigateMock.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it("opens the Data Query page from the header", () => {
    render(
      <Provider store={makeStore(systemInfo as never)}>
        <Header />
      </Provider>,
    )

    fireEvent.click(screen.getByRole("button", { name: /Data Query/i }))

    expect(navigateMock).toHaveBeenCalledWith("/query")
  })
})
