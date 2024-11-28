import styles from './styles.module.scss'
import { useParams } from "react-router-dom"
import { useGetFitsHeaderQuery } from "../../store/api/openapi"
import { useMemo, useState, useEffect, useRef } from "react"
import classNames from 'classnames'


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
    // tableRef内でtr内の最初のtdの要素の内容が`${index}`のものを探して、その要素を取得
    const element = Array.from(tableRef.current?.querySelectorAll('tr td:first-child') ?? [])
      .find(td => td.textContent === `${index}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  return (
    <div className={styles.fitsHeader}>
      <div>
        Jump to HDU:
        {data?.map((_, index) => (
          <button key={index} onClick={() => handleJumpToHDU(index)}>
            {index}
          </button>
        ))}
      </div>
      <div style={{ flexGrow: 1, overflowY: 'auto' }}>
        <table ref={tableRef}>
          <thead>
            <tr>
              <th>HDU Index</th>
              <th>
                Key<br />
                <input
                  type="search"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  ref={searchInputRef}
                />
              </th>
              <th>Value</th>
              <th>Comment</th>
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
