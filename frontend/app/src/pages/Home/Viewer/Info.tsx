import classNames from "classnames"
import { useAppSelector } from "../../../store/hooks"
import { useHomeContext } from "../context"
import { useFocusedAmp, useFocusedCcd, useMouseCursorFocalPlaneCoord } from "../hooks"
import styles from './styles.module.scss'


export function Info() {
  const [x, y] = useMouseCursorFocalPlaneCoord()
  const { quicklookHandle } = useHomeContext()
  const quicklookLayer = quicklookHandle.current?.layer()
  const { value, level } = quicklookLayer?.pixelValue([x, y]) ?? { value: Number.NaN, level: -1 }
  const focusedCcd = useFocusedCcd()
  const focusedAmp = useFocusedAmp()

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
          <tr>
            <th>
              CCD
            </th>
            <td>
              {focusedCcd?.ccd_id.ccd_name}
            </td>
          </tr>
          <tr>
            <th>
              amp
            </th>
            <td>
              {focusedAmp?.amp_id}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
