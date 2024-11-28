import classNames from "classnames"
import { useAppSelector } from "../../../store/hooks"
import { useHomeContext } from "../context"
import { useMouseCursorFocalPlaneCoord } from "../hooks"
import styles from './styles.module.scss'


export function Info() {
  const [x, y] = useMouseCursorFocalPlaneCoord()
  const { quicklookHandle } = useHomeContext()
  const camera = useAppSelector(state => state.home.viewerCamera)
  const quicklookLayer = quicklookHandle.current?.layer()
  const { value, level } = quicklookLayer?.pixelValue([x, y]) ?? { value: Number.NaN, level: -1 }

  return (
    <div className={styles.info} style={{ position: 'absolute', bottom: 0, right: 0 }}>
      <table>
        <tbody>
          <tr>
            <th>x:</th>
            <td>{x.toFixed(2)}</td>
          </tr>
          <tr>
            <th>y:</th>
            <td>{y.toFixed(2)}</td>
          </tr>
          <tr>
            <th>value:</th>
            <td className={classNames(level > 0 && styles.rough)} >
              {Number.isNaN(value) ? 'N/A' : value.toFixed(2)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
