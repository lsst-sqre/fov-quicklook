import { Menu, MenuItem, SubMenu } from "@szhsin/react-menu"
import { memo, useCallback, useMemo, useState } from "react"
import { MaterialSymbol } from "../../../components/MaterialSymbol"
import { parseScopeId } from "../../../quicklookId"
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useListVisitDayCountsQuery } from "../../../store/api/openapi"
import { isValidSearchDate } from "../visitSearch"
import { getInitialCalendarMonth, getSelectedCalendarDate } from "../visitCalendar"
import { VisitCalendarDialog } from "./VisitCalendarDialog"
import styles from "./styles.module.scss"

type SearchBoxProps = {
  onRefresh: () => void
}

export const SearchBox = memo(({ onRefresh }: SearchBoxProps) => {
  const dispatch = useAppDispatch()
  const searchString = useAppSelector((state) => state.home.searchString)
  const dataSource = useAppSelector((state) => state.home.dataSource)
  const currentQuicklook = useAppSelector((state) => state.home.currentQuicklook)
  const listGroupingTimeToleranceDigits = useAppSelector((state) => state.home.listGroupingTimeToleranceDigits)
  const butlerScopes = useAppSelector((state) => state.copyTemplate.butlerScopes)
  const { repositoryName, collection, datasetType } = useMemo(() => parseScopeId(dataSource), [dataSource])
  const [calendarOpen, setCalendarOpen] = useState(false)
  const [calendarMonth, setCalendarMonth] = useState(() => getInitialCalendarMonth(currentQuicklook))
  const { data: calendarVisitDayCounts, isFetching: isCalendarFetching } = useListVisitDayCountsQuery(
    { repositoryName, collection, datasetType, calendarMonth },
    { skip: !calendarOpen },
  )

  const selectedCalendarDate = useMemo(
    () => getSelectedCalendarDate(searchString, currentQuicklook),
    [currentQuicklook, searchString],
  )
  const searchDateValue = isValidSearchDate(searchString) ? searchString : ""

  const closeCalendar = useCallback(() => {
    setCalendarOpen(false)
  }, [])

  const openCalendar = useCallback(() => {
    setCalendarMonth(getInitialCalendarMonth(currentQuicklook))
    setCalendarOpen(true)
  }, [currentQuicklook])

  return (
    <>
      <div className={styles.searchBox}>
        <div style={{ display: "flex" }}>
          <select
            value={dataSource}
            onChange={(event) => dispatch(homeSlice.actions.setDataSource(event.target.value as typeof dataSource))}
            style={{
              flexGrow: 1,
            }}
          >
            {butlerScopes.map((scope) => {
              const key = scope.id ?? ""
              return <option key={key} value={key}>{scope.display_name}</option>
            })}
          </select>
          <Menu
            menuButton={
              <button type="button">
                <MaterialSymbol symbol="settings" />
              </button>
            }
            theming="dark"
          >
            <SubMenu label="Exposure Time Grouping Tolerance">
              {[
                { digits: 100, label: "No grouping" },
                { digits: 0, label: "1 second tolerance" },
                { digits: 1, label: "1 digit (0.1 seconds)" },
                { digits: 2, label: "2 digits (0.01 seconds)" },
                { digits: 3, label: "3 digits (0.001 seconds)" },
              ].map(({ digits, label }) => (
                <MenuItem
                  key={digits}
                  onClick={() => dispatch(homeSlice.actions.setListGroupingTimeToleranceDigits(digits))}
                  type="checkbox"
                  checked={digits === listGroupingTimeToleranceDigits}
                >
                  {label}
                </MenuItem>
              ))}
            </SubMenu>
          </Menu>
          <button onClick={onRefresh} type="button">
            <MaterialSymbol symbol="refresh" />
          </button>
        </div>
        <div className={styles.searchDateField}>
          <input
            aria-label="Observation date"
            className={styles.searchDateInput}
            onChange={(event) => dispatch(homeSlice.actions.setSearchString(event.target.value))}
            type="date"
            value={searchDateValue}
          />
          <button
            aria-label="Open calendar"
            className={styles.searchCalendarButton}
            onClick={openCalendar}
            type="button"
          >
            <MaterialSymbol symbol="calendar_month" />
          </button>
        </div>
      </div>
      {calendarOpen && (
        <VisitCalendarDialog
          calendarMonth={calendarMonth}
          isFetching={isCalendarFetching}
          onCalendarMonthChange={setCalendarMonth}
          onClose={closeCalendar}
          onSelectDate={(date) => {
            dispatch(homeSlice.actions.setSearchString(date))
            closeCalendar()
          }}
          selectedDate={selectedCalendarDate}
          visitDayCounts={calendarVisitDayCounts}
        />
      )}
    </>
  )
})
