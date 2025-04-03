import styles from './styles.module.scss'


type LoadingSpinnerProps = {
  size?: string
  width?: string
  style?: React.CSSProperties
}

export function LoadingSpinner({
  size = '120px',
  width = '10px',
  style,
}: LoadingSpinnerProps) {
  return <span
    style={{
      width: size,
      height: size,
      borderWidth: width,
      ...style,
    }} className={styles.loader}
  />
}
