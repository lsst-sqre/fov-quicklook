import classNames from "classnames"
import { memo, useEffect, useMemo, useState } from "react"
import { LoadingSpinner } from "../../../components/Loading"
import { useListVisitMonthlyCountsQuery } from "../../../store/api/openapi"
import { CcdDataType, homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import {
  buildCalendarDayCounts,
  buildVisitMonthlyCountsQuery,
  dayObsToSearchDate,
  extractListableDataSourceParts,
  getCurrentYearMonth,
  searchDateToDayObs,
} from "../visitSearch"
import styles from "./styles.module.scss"

type VisitAvailabilityDialogProps = {
  dataSource: CcdDataType
  open: boolean
  onClose: () => void
}

const monthOptions = Array.from({ length: 12 }, (_, index) => {
  const value = String(index + 1)

  return { value, label: value }
})

const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const

export const VisitAvailabilityDialog = memo(({ dataSource, open, onClose }: VisitAvailabilityDialogProps) => {
  const dispatch = useAppDispatch()
  const searchString = useAppSelector((state) => state.home.searchString)
  const dataSourceParts = useMemo(() => extractListableDataSourceParts(dataSource), [dataSource])
  const repositoryName = dataSourceParts?.repositoryName ?? ""
  const dataType = dataSourceParts?.dataType ?? ""
  const currentYearMonth = useMemo(() => getCurrentYearMonth(), [])
  const [selectedYear, setSelectedYear] = useState(() => String(currentYearMonth.year))
  const [selectedMonth, setSelectedMonth] = useState(() => String(currentYearMonth.month))
  const year = Number(selectedYear)
  const month = Number(selectedMonth)
  const canQueryMonth = Number.isInteger(year) && year > 0 && month >= 1 && month <= 12
  const currentDayObs = searchDateToDayObs(searchString)

  useEffect(() => {
    if (!open) {
      return
    }

    const next = getCurrentYearMonth()
    setSelectedYear(String(next.year))
    setSelectedMonth(String(next.month))
  }, [open])

  const monthlyCountsResult = useListVisitMonthlyCountsQuery(
    buildVisitMonthlyCountsQuery(
      canQueryMonth ? year : currentYearMonth.year,
      canQueryMonth ? month : currentYearMonth.month,
      dataType,
      repositoryName,
    ),
    { skip: !open || !canQueryMonth || !dataSourceParts },
  )
  const calendarDayCounts = useMemo(
    () => (canQueryMonth ? buildCalendarDayCounts(year, month, monthlyCountsResult.data ?? []) : []),
    [canQueryMonth, month, monthlyCountsResult.data, year],
  )

  if (!open) {
    return null
  }

  const selectDay = (dayObs: number) => {
    dispatch(homeSlice.actions.setSearchString(dayObsToSearchDate(dayObs)))
    onClose()
  }

  return (
    <div className={styles.availabilityBackdrop} onClick={onClose}>
      <div
        aria-labelledby="date-availability-title"
        className={styles.availabilityDialog}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className={styles.availabilityHeader}>
          <h2 className={styles.availabilityTitle} id="date-availability-title">Date availability</h2>
          <button className={styles.availabilityCloseButton} onClick={onClose} type="button">Close</button>
        </div>
        <div className={styles.availabilityFilters}>
          <label className={styles.filterField}>
            <span className={styles.monthFieldLabel}>Year</span>
            <input
              aria-label="Observation year"
              className={styles.yearInput}
              min="1"
              onChange={(event) => setSelectedYear(event.target.value)}
              step="1"
              type="number"
              value={selectedYear}
            />
          </label>
          <label className={styles.filterField}>
            <span className={styles.monthFieldLabel}>Month</span>
            <select
              aria-label="Observation month"
              className={styles.monthSelect}
              onChange={(event) => setSelectedMonth(event.target.value)}
              value={selectedMonth}
            >
              {monthOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>
        <section className={styles.availabilityPanel}>
          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Daily entry counts</h3>
            <span className={styles.panelSource}>{repositoryName}:{dataType}</span>
          </div>
          <p className={styles.panelMessage}>Click a day to update the main date filter.</p>
          {monthlyCountsResult.isFetching ? (
            <div className={styles.panelLoading}>
              <LoadingSpinner />
            </div>
          ) : monthlyCountsResult.isError ? (
            <p className={styles.panelMessage}>Failed to load daily counts.</p>
          ) : (
            <>
              <div className={styles.weekdayHeader}>
                {weekdayLabels.map((label) => (
                  <div className={styles.weekdayLabel} key={label}>{label}</div>
                ))}
              </div>
              <div className={styles.dayGrid}>
                {calendarDayCounts.map((dayCount, index) => (
                  dayCount === null ? (
                    <div className={styles.dayPlaceholder} key={`empty-${index}`} />
                  ) : (
                    <button
                      aria-label={`Set ${dayObsToSearchDate(dayCount.day_obs)} (${dayCount.count} entries)`}
                      className={classNames(
                        styles.dayButton,
                        dayCount.count === 0 && styles.dayButtonEmpty,
                        dayCount.day_obs === currentDayObs && styles.dayButtonSelected,
                      )}
                      disabled={dayCount.count === 0}
                      key={dayCount.day_obs}
                      onClick={() => selectDay(dayCount.day_obs)}
                      type="button"
                    >
                      <span className={styles.dayButtonDate}>{dayCount.day}</span>
                      <span className={styles.dayButtonCount}>{dayCount.count}</span>
                    </button>
                  )
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
})
