import * as styles from './styles.module.scss'


type RoundedFrameProps = {
  children: React.ReactNode
}


export function RoundedFrame({ children }: RoundedFrameProps) {
  return (
    <div className={styles.frame}>
      {children}
    </div>
  )
}