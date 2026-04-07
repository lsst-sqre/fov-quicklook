import classNames from "classnames"
import { memo, useEffect, useMemo, useState } from "react"
import { LoadingSpinner } from "../../../components/Loading"
import { useChangeCurrentQuicklook } from "../../../hooks/useChangeCurrentQuicklook"
import { ListVisitsApiResponse, useListVisitMonthlyCountsQuery, useListVisitsQuery } from "../../../store/api/openapi"
import { CcdDataType, homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch } from "../../../store/hooks"
import {
  buildMonthDayCounts,
  buildVisitMonthlyCountsQuery,
  dayObsToSearchDate,
  getCurrentMonthValue,
} from "../visitSearch"
import styles from "./styles.module.scss"

type VisitAvailabilityDialogProps = {
  dataSource: CcdDataType
  open: boolean
  onClose: () => void
}

type VisitListEntryType = ListVisitsApiResponse[number]

export const VisitAvailabilityDialog = memo(({ dataSource, open, onClose }: VisitAvailabilityDialogProps) => {
  const dispatch = useAppDispatch()
  const changeCurrentQuicklook = useChangeCurrentQuicklook()
  const [monthValue, setMonthValue] = useState(() => getCurrentMonthValue())
  const [selectedDayObs, setSelectedDayObs] = useState<number | undefined>()
  const [repositoryName = "", dataType = ""] = dataSource.split(":")

  const monthlyCountsQuery = useMemo(
    () => buildVisitMonthlyCountsQuery(monthValue, dataType, repositoryName),
    [dataType, monthValue, repositoryName],
  )
  const monthlyCountsResult = useListVisitMonthlyCountsQuery(
    monthlyCountsQuery ?? { year: 1970, month: 1, dataType, repositoryName },
    { skip: !open || monthlyCountsQuery === undefined },
  )
  const dayEntriesResult = useListVisitsQuery(
    selectedDayObs === undefined
      ? { dayObs: 0, dataType, repositoryName, limit: 1000 }
      : { dayObs: selectedDayObs, dataType, repositoryName, limit: 1000 },
    { skip: !open || selectedDayObs === undefined },
  )
  const dayCounts = useMemo(
    () => buildMonthDayCounts(monthValue, monthlyCountsResult.data ?? []),
    [monthValue, monthlyCountsResult.data],
  )
  const selectedDay = useMemo(
    () => dayCounts.find((dayCount) => dayCount.day_obs === selectedDayObs),
    [dayCounts, selectedDayObs],
  )

  useEffect(() => {
    if (open) {
      setSelectedDayObs(undefined)
    }
  }, [dataSource, monthValue, open])

  if (!open) {
    return null
  }

  const selectEntry = (entry: VisitListEntryType) => {
    dispatch(homeSlice.actions.setSearchString(dayObsToSearchDate(entry.day_obs)))
    changeCurrentQuicklook(entry.id)
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
        <label className={styles.monthField}>
          <span className={styles.monthFieldLabel}>Month</span>
          <input
            aria-label="Observation month"
            className={styles.monthInput}
            onChange={(event) => setMonthValue(event.target.value)}
            type="month"
            value={monthValue}
          />
        </label>
        <div className={styles.availabilityColumns}>
          <section className={styles.availabilityPanel}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>Daily entry counts</h3>
            </div>
            {monthlyCountsResult.isFetching ? (
              <div className={styles.panelLoading}>
                <LoadingSpinner />
              </div>
            ) : monthlyCountsResult.isError ? (
              <p className={styles.panelMessage}>Failed to load daily counts.</p>
            ) : (
              <div className={styles.dayGrid}>
                {dayCounts.map((dayCount) => (
                  <button
                    aria-label={`Select ${dayObsToSearchDate(dayCount.day_obs)} (${dayCount.count} entries)`}
                    className={classNames(
                      styles.dayButton,
                      dayCount.count === 0 && styles.dayButtonEmpty,
                      dayCount.day_obs === selectedDayObs && styles.dayButtonSelected,
                    )}
                    disabled={dayCount.count === 0}
                    key={dayCount.day_obs}
                    onClick={() => setSelectedDayObs(dayCount.day_obs)}
                    type="button"
                  >
                    <span className={styles.dayButtonDate}>{dayCount.day}</span>
                    <span className={styles.dayButtonCount}>{dayCount.count}</span>
                  </button>
                ))}
              </div>
            )}
          </section>
          <section className={styles.availabilityPanel}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>
                {selectedDay ? `Entries on ${dayObsToSearchDate(selectedDay.day_obs)}` : "Entries"}
              </h3>
              {selectedDay && <span className={styles.panelCount}>{selectedDay.count}</span>}
            </div>
            {selectedDayObs === undefined ? (
              <p className={styles.panelMessage}>Select a day to view entries.</p>
            ) : dayEntriesResult.isFetching ? (
              <div className={styles.panelLoading}>
                <LoadingSpinner />
              </div>
            ) : dayEntriesResult.isError ? (
              <p className={styles.panelMessage}>Failed to load entries.</p>
            ) : (dayEntriesResult.data?.length ?? 0) === 0 ? (
              <p className={styles.panelMessage}>No entries found for this day.</p>
            ) : (
              <ul className={styles.entrySelectionList}>
                {dayEntriesResult.data?.map((entry) => (
                  <li key={entry.id}>
                    <button
                      className={styles.entrySelectionButton}
                      onClick={() => selectEntry(entry)}
                      type="button"
                    >
                      <span className={styles.entrySelectionId}>{entry.id.split(":").slice(-1)[0]}</span>
                      <span className={styles.entrySelectionMeta}>
                        {[entry.obs_id, entry.physical_filter, `${entry.exposure_time}s`].filter(Boolean).join(" · ")}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  )
})
