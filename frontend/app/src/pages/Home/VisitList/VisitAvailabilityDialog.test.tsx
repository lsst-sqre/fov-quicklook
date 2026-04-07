import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { homeSlice } from "../../../store/features/homeSlice"
import { VisitAvailabilityDialog } from "./VisitAvailabilityDialog"

const dispatch = vi.fn()
const changeCurrentQuicklook = vi.fn()
const useListVisitMonthlyCountsQuery = vi.fn()
const useListVisitsQuery = vi.fn()

vi.mock("../../../store/hooks", () => ({
  useAppDispatch: () => dispatch,
}))

vi.mock("../../../hooks/useChangeCurrentQuicklook", () => ({
  useChangeCurrentQuicklook: () => changeCurrentQuicklook,
}))

vi.mock("../../../store/api/openapi", () => ({
  useListVisitMonthlyCountsQuery: (...args: unknown[]) => useListVisitMonthlyCountsQuery(...args),
  useListVisitsQuery: (...args: unknown[]) => useListVisitsQuery(...args),
}))

describe("VisitAvailabilityDialog", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2025, 4, 1))
    dispatch.mockReset()
    changeCurrentQuicklook.mockReset()
    useListVisitMonthlyCountsQuery.mockReset()
    useListVisitsQuery.mockReset()

    useListVisitMonthlyCountsQuery.mockReturnValue({
      data: [{ day_obs: 20250519, count: 2 }],
      isFetching: false,
      isError: false,
    })
    useListVisitsQuery.mockImplementation((query: { dayObs: number }) => ({
      data: query.dayObs === 20250519
        ? [{
          day_obs: 20250519,
          exposure_time: 30,
          id: "embargo:raw:2025051900437",
          obs_id: "obs-437",
          observation_reason: "science",
          observation_type: "science",
          physical_filter: "r",
          science_program: "program-1",
          target_name: "target-1",
        }]
        : [],
      isFetching: false,
      isError: false,
    }))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("shows daily counts and selects an entry from the chosen day", () => {
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

    fireEvent.click(screen.getByRole("button", { name: "Select 2025-05-19 (2 entries)" }))

    fireEvent.click(screen.getByRole("button", { name: /2025051900437/ }))

    expect(dispatch).toHaveBeenCalledWith(homeSlice.actions.setSearchString("2025-05-19"))
    expect(changeCurrentQuicklook).toHaveBeenCalledWith("embargo:raw:2025051900437")
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
