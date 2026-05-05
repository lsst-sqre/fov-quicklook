import { MenuItem, MenuItemProps } from "@szhsin/react-menu"
import styles from './styles.module.scss'


type Props = MenuItemProps & {
  annotation: string
}


export function MenuItemWithAnnotation(
  {
    annotation,
    children,
    ...rests
  }: Props,
) {
  return (
    <MenuItem {...rests}>
      <div className={styles.menuItemWithAnnotation}>
        <div className={styles.menuItemWithAnnotationBody}>{children as any}</div>
        <div>{annotation}</div>
      </div>
    </MenuItem>
  )
}
