import { SkyCoord, angle } from '@stellar-globe/stellar-globe'
import { Fragment, Suspense, memo, useCallback, useMemo } from "react"
import { ErrorBoundary } from "react-error-boundary"
import { Icon } from '../../../common/components/Icon'
import { Linkify } from '../../../common/components/Linkify'
import { Loader } from '../../../common/components/Loader'
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { AppDialog } from '../../AppDialog'
import { useAppContext } from '../../context'
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { hipsLayersSlice } from './hipsLayersSlice'
import { HipsMenu } from './hipsMenu'
import styles from './style.module.scss'
import { resizableY } from '@stellar-globe/react-draggable-dialog'
import { HipsProperties, parseHipsProperties } from './HipsProperties'


export const HipsDialog = memo(() => {
  const currentBaseUrl = useAppSelector(state => state.hipsLayers.baseUrl)
  const dispatch = useAppDispatch()
  const visible = useAppSelector(state => state.hipsLayers.hipsDialogVisible)

  return (
    <AppDialog
      title={<Fragment><Icon type="layers" marginRight />HiPS</Fragment>}
      visible={visible}
      onCloseButtonClick={() => dispatch(hipsLayersSlice.actions.hipsDialogToggled({}))}
      resizable={resizableY}
      sizeHint={{ width: '400px' }}
      minmaxSize={{ maxHeight: '600px' }}
      menu={<HipsMenu />}
    >
      {currentBaseUrl && (
        <ErrorBoundary fallback={<Icon type='error' />}>
          <Suspense fallback={<Loader />}>
            <HipsInspector baseUrl={currentBaseUrl} />
          </Suspense>
        </ErrorBoundary>
      )}
    </AppDialog>
  )
})


type HipsInspectorProps = {
  baseUrl: string
}

const HipsInspector = memo(({ baseUrl }: HipsInspectorProps) => {
  const properties = useHipsProperties(baseUrl)

  const initialPosition = useMemo(() => {
    const safeNumber = (s: string | undefined) => {
      const n = Number(s)
      return Number.isFinite(n) ? n : undefined
    }
    const fov = safeNumber(properties.cards.find(c => c.key === 'hips_initial_fov')?.value)
    const ra = safeNumber(properties.cards.find(c => c.key === 'hips_initial_ra')?.value)
    const dec = safeNumber(properties.cards.find(c => c.key === 'hips_initial_dec')?.value)
    if (ra !== undefined && dec !== undefined) {
      return { ra, dec, fov }
    }
  }, [properties])

  const { globeHandle } = useAppContext()

  const goToInitialPosition = useCallback(() => {
    if (initialPosition) {
      const { ra, dec, fov } = initialPosition
      globeHandle.current!().camera.jumpTo({ fovy: fov ? angle.deg2rad(fov) : angle.amin2rad(1) }, { coord: SkyCoord.fromDeg(ra, dec) })
    }
  }, [globeHandle, initialPosition])

  const title = useMemo(() => properties.cards.find(c => c.key === 'obs_title')?.value, [properties])

  return (
    <table className={styles.hipsInspector}>
      <caption>{title}</caption>
      <tbody>
        {properties.cards.map((card, index) => (
          <tr key={index}>
            <th>{
              initialPosition && card.key.match(/hips_initial_(?:ra|dec|fov)$/)
                ? <a href="./" onClick={e => { e.preventDefault(); goToInitialPosition() }}>{card.key}</a>
                : card.key
            }</th>
            <td>
              <Linkify text={card.value} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
})

setDisplayName({ HipsInspector })


const cache = new Map<string, { promise: Promise<void>, result?: HipsProperties, error?: any }>()


function useHipsProperties(baseUrl: string) {
  if (!cache.has(baseUrl)) {
    const promise = (async () => {
      try {
        const result = parseHipsProperties(await (await fetch(`${baseUrl}/properties`)).text())
        cache.get(baseUrl)!.result = result
      }
      catch (error) {
        cache.get(baseUrl)!.error = error
      }
    })()
    cache.set(baseUrl, { promise })
  }
  const { promise, result, error } = cache.get(baseUrl)!
  if (result) {
    return result
  }
  throw error ?? promise
}
