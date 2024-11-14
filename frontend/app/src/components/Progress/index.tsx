import { memo } from "react"
import * as styles from './styles.module.scss'
import classNames from "classnames"

type PropgressProps = {
  count: number
  total: number
  width?: string
}

export const Progress = memo(({ count, total, width: boxWidth = '600px' }: PropgressProps) => {
  const width = total === 0 ? '0' : `${(count / total) * 100}%`
  return (
    <div className={styles.background} style={{ width: boxWidth }} >
      <div className={classNames(styles.bar, count === total && styles.completed)} style={{ width }} />
    </div>
  )
})
