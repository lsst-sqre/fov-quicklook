import classNames from 'classnames'
import styles from './styles.module.scss'

export function FrostedGlass({ children, style, className }: {
  children: React.ReactNode,
  style?: React.CSSProperties, className?: string,
}) {
  return (
    <div style={style} className={classNames(styles.frostedglass, className)}>
      {children}
    </div>
  )
}
