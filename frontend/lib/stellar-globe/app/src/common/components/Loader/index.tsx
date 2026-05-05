import { CSSProperties, memo } from 'react'
import { setDisplayName } from '../../utils/setDisplayName'
import styles from './style.module.scss'


type Props = {
  size?: CSSProperties['width']
  borderWidth?: CSSProperties['borderWidth']
  color?: CSSProperties['color']
  padding?: CSSProperties['padding']
}


export const Loader = memo(({
  size = `48px`,
  borderWidth = '5px',
  color = 'rgba(255, 255, 255, 0.5)',
  padding = '8px',
}: Props = {}) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
        padding,
      }}
    >
      <div
        style={{
          width: size,
          height: size,
          border: `${borderWidth} solid ${color}`,
          borderBottomColor: 'transparent',
        }}
        className={styles.loader}
      />
    </div>
  )
})

setDisplayName({ Loader })


export const SmallLoader = memo(({
  color,
}: Pick<Props, 'color'>) => {
  // size = `48px`,
  //   borderWidth = '5px',
  //   color = 'rgba(255, 255, 255, 0.5)',
  //   padding = '8px',


  return (
    <div style={{ margin: '0 8px' }}>
      <Loader
        color={color}
        size='20px'
        borderWidth='2px'
        padding='1px 0'
      />
    </div>
  )
})
setDisplayName({ SmallLoader })
