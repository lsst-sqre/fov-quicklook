import classNames from "classnames"
import { FormEvent, memo, useCallback, useEffect, useMemo, useState } from "react"
import { MaterialSymbol } from "../../../components/MaterialSymbol"
import { LoadingSpinner } from "../../../components/Loading"
import homeStyles from "../styles.module.scss"
import {
  buildCalendarDayCells,
  buildVisitCountsByDate,
  getCalendarDayCountDisplay,
  parseCalendarMonthInput,
  shiftCalendarMonth,
} from "../visitCalendar"
import styles from "./styles.module.scss"

type VisitCalendarDialogProps = {
  calendarMonth: string
  isFetching: boolean
  onCalendarMonthChange: (month: string) => void
  onClose: () => void
  onSelectDate: (date: string) => void
  selectedDate: string | undefined
  visitDayCounts: { day_obs: number, count: number }[] | undefined
}

export const VisitCalendarDialog = memo(({
  calendarMonth,
  isFetching,
  onCalendarMonthChange,
  onClose,
  onSelectDate,
  selectedDate,
  visitDayCounts,
}: VisitCalendarDialogProps) => {
  const [monthInput, setMonthInput] = useState(calendarMonth)
  const calendarDayCells = useMemo(
    () => buildCalendarDayCells(calendarMonth),
    [calendarMonth],
  )
  const visitCountsByDate = useMemo(
    () => buildVisitCountsByDate(visitDayCounts, calendarMonth),
    [calendarMonth, visitDayCounts],
  )

  useEffect(() => {
    setMonthInput(calendarMonth)
  }, [calendarMonth])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose()
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => {
      window.removeEventListener("keydown", onKeyDown)
    }
  }, [onClose])

  const commitMonthInput = useCallback(() => {
    const nextMonth = parseCalendarMonthInput(monthInput)
    if (!nextMonth) {
      setMonthInput(calendarMonth)
      return
    }
    onCalendarMonthChange(nextMonth)
  }, [calendarMonth, monthInput, onCalendarMonthChange])

  const handleMonthSubmit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    commitMonthInput()
  }, [commitMonthInput])

  return (
    <div className={homeStyles.shortcutHelpBackdrop} onClick={onClose}>
      <div
        aria-label="Observation calendar"
        aria-modal="true"
        className={classNames(homeStyles.shortcutHelpDialog, styles.calendarDialog)}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className={classNames(homeStyles.shortcutHelpHeader, styles.calendarHeader)}>
          <button
            aria-label="Previous month"
            className={styles.calendarMonthButton}
            onClick={() => onCalendarMonthChange(shiftCalendarMonth(calendarMonth, -1))}
            type="button"
          >
            <MaterialSymbol symbol="chevron_left" />
          </button>
          <form className={styles.calendarTitle} onSubmit={handleMonthSubmit}>
            <input
              aria-label="Select month"
              className={styles.calendarMonthInput}
              inputMode="numeric"
              onBlur={commitMonthInput}
              onChange={(event) => setMonthInput(event.target.value)}
              placeholder="YYYY-MM"
              spellCheck={false}
              type="text"
              value={monthInput}
            />
          </form>
          <button
            aria-label="Next month"
            className={styles.calendarMonthButton}
            onClick={() => onCalendarMonthChange(shiftCalendarMonth(calendarMonth, 1))}
            type="button"
          >
            <MaterialSymbol symbol="chevron_right" />
          </button>
        </div>
        <div className={styles.calendarBody}>
          <div className={styles.calendarWeekdays}>
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <span className={styles.calendarWeekday} key={day}>{day}</span>
            ))}
          </div>
          <div className={styles.calendarGrid}>
            {calendarDayCells.map((cell) => {
              const dayCountDisplay = getCalendarDayCountDisplay(cell, visitCountsByDate)

              return (
                <button
                  className={classNames(
                    styles.calendarDay,
                    dayCountDisplay.isEmpty && cell.inCurrentMonth && styles.calendarDayEmpty,
                    !cell.inCurrentMonth && styles.calendarDayOutsideMonth,
                    selectedDate === cell.date && styles.calendarDaySelected,
                  )}
                  disabled={isFetching}
                  key={cell.date}
                  onClick={() => {
                    if (!cell.inCurrentMonth) {
                      onCalendarMonthChange(cell.date.slice(0, 7))
                      return
                    }
                    onSelectDate(cell.date)
                  }}
                  type="button"
                >
                  <span className={styles.calendarDayLabel}>
                    <span className={styles.calendarDayNumber}>{cell.day}</span>
                    <span className={classNames(styles.calendarDayCount, dayCountDisplay.isEmpty && styles.calendarDayCountEmpty)}>
                      {dayCountDisplay.value}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
          {isFetching && (
            <div className={styles.calendarLoadingOverlay}>
              <LoadingSpinner />
            </div>
          )}
        </div>
      </div>
    </div>
  )
})
