import classNames from "classnames"
import { HTMLAttributes, ReactNode, forwardRef } from "react"
import { setDisplayName } from "../../utils/setDisplayName"
import styles from './styles.module.scss'


type Props = {
  children?: ReactNode
} & HTMLAttributes<HTMLDivElement>


export const MenuBar = forwardRef<HTMLDivElement, Props>(({ children, className, ...rests }, ref) => {
  return (
    <div ref={ref} className={classNames(className, styles.menuBar)} {...rests}>
      {children}
    </div>
  )
})

setDisplayName({ MenuBar })
