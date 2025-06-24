import classNames from 'classnames'
import { useEffect, useMemo, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { useGetFitsHeaderQuery } from "../../store/api/openapi"
import styles from './styles.module.scss'


export function FItsHeaderPage() {
  const { visitId, ccdName } = useParams<{ visitId: string, ccdName: string }>()
  return visitId && ccdName && <FitsHeader visitId={visitId} ccdName={ccdName} />
}


type FitsHeaderProps = {
  visitId: string
  ccdName: string
}


function FitsHeader({ ccdName: ccdId, visitId }: FitsHeaderProps) {
  const { data } = useGetFitsHeaderQuery({ id: visitId, ccdName: ccdId })
  const [searchTerm, setSearchTerm] = useState("")
  const searchInputRef = useRef<HTMLInputElement>(null)
  const tableRef = useRef<HTMLTableElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const jumpDivRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  const filteredCards = useMemo(() => {
    return data?.flatMap((cards, index) =>
      cards.filter(([key]) => key.toLowerCase().includes(searchTerm.toLowerCase()))
        .map(card => [index, ...card] as const)
    ) ?? []
  }, [data, searchTerm])


  const handleJumpToHDU = (index: number) => {
    const element = Array.from(tableRef.current?.querySelectorAll('tr td:first-child') ?? [])
      .find(td => td.textContent === `${index}`)

    if (element && scrollContainerRef.current) {
      const totalStickyHeight = calculateStickyHeadersHeight(jumpDivRef, tableRef)

      // スクロールコンテナ内の要素の相対位置を計算
      const containerRect = scrollContainerRef.current.getBoundingClientRect()
      const elementRect = element.getBoundingClientRect()
      const relativeTop = elementRect.top - containerRect.top + scrollContainerRef.current.scrollTop

      // スクロール位置を調整
      scrollContainerRef.current.scrollTo({
        top: relativeTop - totalStickyHeight,
        behavior: 'smooth'
      })
    }
  }

  return (
    <div className={styles.fitsHeader}>
      <div
        ref={jumpDivRef}
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 2,
        }}
      >
        Jump to HDU:
        {data?.map((_, index) => (
          <button key={index} onClick={() => handleJumpToHDU(index)}>
            {index}
          </button>
        ))}
      </div>
      <div
        ref={scrollContainerRef}
        style={{ flexGrow: 1, overflowY: 'auto' }}
      >
        <table ref={tableRef}>
          <thead>
            <tr>
              {['HDU Index', 'Key', 'Value', 'Comment'].map((header, i) => (
                <th key={i}>
                  {header}
                  {header === 'Key' && (
                    <>
                      <br />
                      <input
                        type="search"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        ref={searchInputRef}
                      />
                    </>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredCards.map(([hduIndex, key, type, value, comment], i) => (
              <tr key={i} className={classNames((hduIndex & 1) === 1 && styles.odd)} >
                <td>{hduIndex}</td>
                <td>{key}</td>
                <td className={(styles as any)[type]} >{value}</td>
                <td>{comment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const calculateStickyHeadersHeight = (jumpDivRef: React.RefObject<HTMLDivElement>, tableRef: React.RefObject<HTMLTableElement>): number => {
  let totalHeight = 0;
  
  // Jump to HDU divの高さを追加
  if (jumpDivRef.current) {
    totalHeight += jumpDivRef.current.getBoundingClientRect().height;
  }
  
  // theadの高さを追加
  if (tableRef.current) {
    const thead = tableRef.current.querySelector('thead');
    if (thead) {
      totalHeight += thead.getBoundingClientRect().height;
    }
  }
  
  return totalHeight;
}
