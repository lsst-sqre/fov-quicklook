import { memo } from "react"
import * as styles from './styles.module.scss'
import classNames from "classnames"

type PropgressProps = {
  count: number
  total: number
  width?: string
  rounded?: boolean
}

export const Progress = memo(({ count, total, width: boxWidth = '600px', rounded = false }: PropgressProps) => {
  const width = total === 0 ? '0' : `${(count / total) * 100}%`
  return (
    <div className={classNames(styles.background, rounded && styles.rounded)} style={{ width: boxWidth }} >
      <div className={classNames(styles.bar, count > 0 && count === total && styles.completed, rounded && styles.rounded)} style={{ width }} />
    </div>
  )
})
