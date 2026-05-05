import styles from './styles.module.scss'
import { Fragment, memo, useCallback } from "react"
import { AppDialog } from "../../AppDialog"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { fitsImageSlice } from "./fitsImageSlice"
import { Icon } from '../../../common/components/Icon'
import EditableDiv from '../../../common/components/EditableDiv'
import { ColorPickerRgba } from '../../../common/components/ColorPicker'

export const FitsImagesDialog = memo(() => {
  const dispatch = useAppDispatch()
  const visible = useAppSelector(state => state.fitsImage.dialogVisible)
  const images = useAppSelector(state => state.fitsImage.images)

  const addMaskURL = useCallback(() => {
    const url = prompt('Enter URL')
    if (url) {
      const name = url.split('/').filter(Boolean).pop() ?? ''
      dispatch(fitsImageSlice.actions.imageAdded({
        url,
        name,
        hduIndex: 0,
        maskConfig: { maskBit: 8, color: [1, 0, 1, 1] },
      }))
    }
  }, [dispatch])

  return (
    <AppDialog
      title={<Fragment>Mask Viewer</Fragment>}
      visible={visible}
    >
      <table>
        <thead>
          <tr>
            <th>Name</th>
            {/* <th>URL</th> */}
            <th>Bit</th>
            <th>Color</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {images.map(image => (
            <tr key={image.id}>
              <td className={styles.name}>{image.name}</td>
              <td>
                <EditableDiv value={String(image.maskConfig.maskBit)} onChange={e => dispatch(fitsImageSlice.actions.imageMaskConfigUpdated({ id: image.id, maskConfig: { maskBit: Number(e) } }))} />
              </td>
              <td>
                <ColorPickerRgba color={image.maskConfig.color} onChange={color => dispatch(fitsImageSlice.actions.imageMaskConfigUpdated({ id: image.id, maskConfig: { color } }))} />
              </td>
              {/* <td className={styles.url} >{image.url}</td> */}
              <td>
                <button onClick={() => dispatch(fitsImageSlice.actions.imageRemoved({ id: image.id }))} ><Icon type='delete' /></button>
              </td>
            </tr>
          ))}
          <tr>
            <td colSpan={4}>
              <button onClick={addMaskURL} ><Icon type='add' /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </AppDialog>
  )
})
