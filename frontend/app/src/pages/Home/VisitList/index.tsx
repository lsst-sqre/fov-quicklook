import classNames from 'classnames'
import React, { memo, useEffect, useMemo, useRef } from "react"
import { MaterialSymbol } from '../../../components/MaterialSymbol'
import { ListVisitsApiArg, ListVisitsApiResponse, useListVisitsQuery } from "../../../store/api/openapi"
import { homeSlice } from '../../../store/features/homeSlice'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import styles from './styles.module.scss'
import { LoadingSpinner } from '../../../components/Loading'
import { useChangeCurrentQuicklook } from '../../../hooks/useChangeCurrentQuicklook'


type VisitListProps = {
  style?: React.CSSProperties
}


function isValidSearchString(s: string) {
  // 20241021 or 2024102100002
  return /^\d{8}(\d{5})?$/.test(s)
}

function useVisitList() {
  const searchString = useAppSelector(state => state.home.searchString)
  const dataSource = useAppSelector(state => state.home.dataSource)
  const query = useMemo(() => {

    if (isValidSearchString(searchString)) {
      switch (searchString.length) {
        case 8:
          return { dayObs: Number(searchString), dataType: dataSource }
        case 13:
          return { exposure: Number.parseInt(searchString), dataType: dataSource }
      }
    }
    return {
      dataType: dataSource,
    } as ListVisitsApiArg
  }, [dataSource, searchString])
  const { data: list, refetch, isFetching } = useListVisitsQuery(query)
  return { list, refetch, isFetching }
}

// exposure_timeが同等かどうかを判定する関数
function isEquivalentExposureTime(a: number, b: number): boolean {
  // 小数点第2位で四捨五入して比較
  return Math.round(a * 100) / 100 === Math.round(b * 100) / 100
}

// グループが同じかどうかを判定する関数
function isSameGroup(a: VisitListEntryType, b: VisitListEntryType): boolean {
  return a.day_obs === b.day_obs &&
    a.physical_filter === b.physical_filter &&
    isEquivalentExposureTime(a.exposure_time, b.exposure_time) &&
    a.observation_type === b.observation_type
}

// リストをグループに分割する関数
function groupVisitList(list: VisitListEntryType[] | undefined): VisitListEntryType[][] {
  if (!list || list.length === 0) return []

  const result: VisitListEntryType[][] = []
  let currentGroup: VisitListEntryType[] = [list[0]]

  for (let i = 1; i < list.length; i++) {
    if (isSameGroup(list[i - 1], list[i])) {
      currentGroup.push(list[i])
    } else {
      result.push(currentGroup)
      currentGroup = [list[i]]
    }
  }

  if (currentGroup.length > 0) {
    result.push(currentGroup)
  }

  return result
}

// スクロールコンテナを管理するためのコンテキスト
const ListScrollContainerContext = React.createContext<React.RefObject<HTMLDivElement> | null>(null)

export const VisitList = memo(({ style }: VisitListProps) => {
  const { list, isFetching } = useVisitList()
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const dispatch = useAppDispatch()
  const changeCurrentQuicklook = useChangeCurrentQuicklook()
  const listContainerRef = useRef<HTMLDivElement>(null)

  // リストをグループ化
  const groupedList = useMemo(() => groupVisitList(list), [list])

  useEffect(() => {
    if (currentQuicklook === undefined && list?.length) {
      changeCurrentQuicklook(list[0].id)
    }
  }, [changeCurrentQuicklook, currentQuicklook, list])

  return (
    <div className={styles.listWrapper}>
      <SearchBox />
      <div className={styles.listContainer}>
        <ListScrollContainerContext.Provider value={listContainerRef}>
          <div className={styles.list} style={style} ref={listContainerRef}>
            {groupedList.map((group, index) => (
              <VisitGroup key={index} group={group} />
            ))}
          </div>
        </ListScrollContainerContext.Provider>
        {isFetching && <div className={styles.loadingOverlay}><LoadingSpinner /></div>}
      </div>
    </div>
  )
})

// グループを表示するコンポーネント
function VisitGroup({ group }: { group: VisitListEntryType[] }) {
  if (!group.length) return null

  const firstEntry = group[0]
  const roundedExposureTime = Math.round(firstEntry.exposure_time * 100) / 100
  const isRounded = roundedExposureTime !== firstEntry.exposure_time
  // 丸めた値を文字列で表示（小数点以下の不要な0は表示しない）
  const exposureTimeDisplay = `${isRounded ? '~' : ''}${roundedExposureTime}`

  return (
    <div className={styles.group}>
      <div className={styles.groupHeader}>
        <div className={styles.headerItem} title="Filter">
          <span>{firstEntry.physical_filter}</span>
        </div>
        <div className={styles.headerItem} title="Exposure Time">
          <span>{exposureTimeDisplay}</span>
        </div>
        <div className={styles.headerItem} title="Type">
          <span>{firstEntry.observation_type}</span>
        </div>
        <div className={styles.headerItem} title="Program">
          <span>{firstEntry.science_program}</span>
        </div>
        <div className={styles.headerItem} title="Reason">
          <span>{firstEntry.observation_reason}</span>
        </div>
        <div className={styles.headerItem} title="Target">
          <span>{firstEntry.target_name}</span>
        </div>
      </div>
      <div className={styles.groupEntries}>
        {group.map((entry) => (
          <VisitListEntry key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  )
}

type VisitListEntryType = ListVisitsApiResponse[number]


function VisitListEntry({ entry }: { entry: VisitListEntryType }) {
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const selected = currentQuicklook?.split(':')[1] === entry.id.split(':')[1]
  const entryRef = useRef<HTMLDivElement>(null)
  const listContainerRef = React.useContext(ListScrollContainerContext)
  const changeCurrentQuicklook = useChangeCurrentQuicklook()

  const select = () => {
    changeCurrentQuicklook(entry.id)
  }

  useEffect(() => {
    if (selected && entryRef.current && listContainerRef) {
      scrollToElementBelowSticky(entryRef, listContainerRef)
    }
  }, [selected, listContainerRef])

  return (
    <div
      ref={entryRef}
      className={classNames(styles.entry, selected && styles.selected)}
      onClick={select}
      title={`obs_id: ${entry.obs_id};\nexposure_time: ${entry.exposure_time}s`}
    >
      {entry.id.split(':').slice(-1)[0]}
    </div>
  )
}

// stickyな要素の下に要素が見えるようにスクロールする関数
function scrollToElementBelowSticky(
  elementRef: React.RefObject<HTMLElement>,
  containerRef: React.RefObject<HTMLDivElement>
) {
  if (!elementRef.current || !containerRef.current) {
    console.log('DEBUG: 要素またはコンテナが見つかりません')
    return
  }

  const container = containerRef.current
  const element = elementRef.current
  const elementRect = element.getBoundingClientRect()
  const containerRect = container.getBoundingClientRect()
  
  // console.log('DEBUG: 対象要素:', element)
  // console.log('DEBUG: コンテナ:', container)
  // console.log('DEBUG: 要素の位置:', {
  //   top: elementRect.top,
  //   bottom: elementRect.bottom,
  //   height: elementRect.height
  // })
  // console.log('DEBUG: コンテナの位置:', {
  //   top: containerRect.top,
  //   bottom: containerRect.bottom,
  //   scrollTop: container.scrollTop,
  //   height: containerRect.height
  // })

  // 要素の位置をコンテナ内の相対位置に変換
  const elementRelativeTop = elementRect.top - containerRect.top + container.scrollTop
  // console.log('DEBUG: 相対位置:', elementRelativeTop)

  // 最も近いグループ要素（sticky要素の親）を見つける
  const closestGroup = element.closest(`.${styles.group}`)
  // console.log('DEBUG: 最も近いグループ:', closestGroup)
  
  if (!closestGroup) {
    // console.log('DEBUG: グループが見つからないため通常スクロール')
    // グループが見つからない場合は通常のスクロール
    // 注: scrollIntoViewはコンテナ要素のコンテキストで実行されないため修正
    container.scrollTop = elementRelativeTop - containerRect.height / 2 + elementRect.height / 2
    return
  }

  // グループヘッダーの高さを取得
  const groupHeader = closestGroup.querySelector(`.${styles.groupHeader}`)
  // console.log('DEBUG: グループヘッダー:', groupHeader)
  
  const headerHeight = groupHeader ? groupHeader.getBoundingClientRect().height : 0
  // console.log('DEBUG: ヘッダーの高さ:', headerHeight)

  // 要素が画面の上部に隠れる場合、stickyヘッダーの下に表示されるようにスクロール
  const isHiddenByHeader = elementRect.top < containerRect.top + headerHeight
  const isHiddenAtBottom = elementRect.bottom > containerRect.bottom
  
  // console.log('DEBUG: ヘッダーに隠れている:', isHiddenByHeader)
  // console.log('DEBUG: 下部に隠れている:', isHiddenAtBottom)

  if (isHiddenByHeader) {
    const scrollTop = elementRelativeTop - headerHeight - 8 // 8pxの余白を追加
    // console.log('DEBUG: 新しいスクロール位置(上部調整):', scrollTop)
    
    container.scrollTo({
      top: scrollTop,
      behavior: 'smooth'
    })
  } else if (isHiddenAtBottom) {
    // console.log('DEBUG: 下部調整スクロール実行')
    // コンテナ内でのスクロール位置を計算
    const bottomAdjustment = elementRelativeTop - containerRect.height + elementRect.height + 8
    // console.log('DEBUG: 新しいスクロール位置(下部調整):', bottomAdjustment)
    
    container.scrollTo({
      top: bottomAdjustment,
      behavior: 'smooth'
    })
  } else {
    // console.log('DEBUG: スクロール不要')
  }
}

function SearchBox() {
  const dispatch = useAppDispatch()
  const searchString = useAppSelector(state => state.home.searchString)
  const dataSource = useAppSelector(state => state.home.dataSource)
  const { refetch } = useVisitList()

  return (
    <div className={styles.searchBox}>
      <div style={{ display: 'flex' }} >
        <select
          value={dataSource}
          onChange={e => dispatch(homeSlice.actions.setDataSource(e.target.value as typeof dataSource))}
          style={{
            flexGrow: 1,
          }}
        >
          <option value="raw">Raw</option>
          <option value="post_isr_image">Post-ISR (recent)</option>
          <option value="preliminary_visit_image">Preliminary PVI (recent)</option>
        </select>
        <button onClick={refetch}>
          <MaterialSymbol symbol='refresh' />
        </button>
      </div>
      <input
        type="search"
        placeholder='Date or Exposure ex. 20241204 or 2024120400003'
        value={searchString}
        onChange={e => dispatch(homeSlice.actions.setSearchString(e.target.value))}
        style={{
          color: isValidSearchString(searchString) ? 'white' : 'gray',
        }}
      />
    </div>
  )
}
