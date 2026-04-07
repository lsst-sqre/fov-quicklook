import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { homeSlice } from "../../../store/features/homeSlice"
import { VisitAvailabilityDialog } from "./VisitAvailabilityDialog"

const dispatch = vi.fn()
const useListVisitMonthlyCountsQuery = vi.fn()

vi.mock("../../../store/hooks", () => ({
  useAppDispatch: () => dispatch,
  useAppSelector: (selector: (state: { home: { searchString: string } }) => unknown) => selector({
    home: {
      searchString: "",
    },
  }),
}))

vi.mock("../../../store/api/openapi", () => ({
  useListVisitMonthlyCountsQuery: (...args: unknown[]) => useListVisitMonthlyCountsQuery(...args),
}))

describe("VisitAvailabilityDialog", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2025, 4, 1))
    dispatch.mockReset()
    useListVisitMonthlyCountsQuery.mockReset()

    useListVisitMonthlyCountsQuery.mockReturnValue({
      data: [{ day_obs: 20250519, count: 2 }],
      isFetching: false,
      isError: false,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("shows daily counts for the current data source and updates the main date filter when a day is clicked", () => {
    const onClose = vi.fn()

    render(<VisitAvailabilityDialog dataSource="embargo:raw" onClose={onClose} open />)

    expect(useListVisitMonthlyCountsQuery).toHaveBeenCalledWith(
      {
        year: 2025,
        month: 5,
        dataType: "raw",
        repositoryName: "embargo",
      },
      { skip: false },
    )
    expect(screen.getByText("embargo:raw")).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: "Set 2025-05-19 (2 entries)" }))

    expect(dispatch).toHaveBeenCalledWith(homeSlice.actions.setSearchString("2025-05-19"))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
