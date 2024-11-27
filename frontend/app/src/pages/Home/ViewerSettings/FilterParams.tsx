import { LogScaleRange } from "@stellar-globe/react-stellar-globe"
import { memo, useCallback, useEffect, useState } from "react"
import { RubinImageFilterParams } from "../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter"
import { QuicklookMetadata } from "../../../store/api/openapi"
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useHomeContext } from "../context"
import styles from './styles.module.scss'

export const FilterParams = memo(() => {
  const dispatch = useAppDispatch()
  const params = useAppSelector(state => state.home.filterParams)
  const { currentQuicklook } = useHomeContext()
  const metadata = currentQuicklook.metadata
  const { min, max, colormap, scale, gamma } = params
  const [barMinMax, setBarMinMax] = useState<[number, number]>([-1, 1])

  const setParams = useCallback((params: RubinImageFilterParams) => {
    dispatch(homeSlice.actions.setFilterParams(params))
  }, [dispatch])

  useEffect(function onTileMetaChanged() {
    if (metadata) {
      const [min, max] = autoBarMinMax(metadata)
      setBarMinMax([min, max])
      setParams({ ...params, ...autoMinMax(metadata) })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metadata])

  const reset = useCallback(() => {
    console.log({ metadata })
    if (metadata) {
      setParams({ ...params, ...autoMinMax(metadata), gamma: 0, colormap: 'Gray' })
    }
  }, [metadata, setParams, params])

  return (
    <div className={styles.filterParams}>
      <dl>
        <dt>ScaleFunction</dt>
        <dd>
          <select value={scale} onChange={e => setParams({ ...params, scale: e.currentTarget.value as any })}>
            <option value="Linear">Linear</option>
            <option value="Arsinh">Arsinh</option>
          </select>
        </dd>
        <dt>ColorMap</dt>
        <dd>
          <select value={colormap} onChange={e => setParams({ ...params, colormap: e.currentTarget.value as any })}>
            {
              colorMaps.map(cm => (
                <option key={cm} value={cm}>{cm}</option>
              ))
            }
          </select>
        </dd>
        <dt>gamma = {gamma.toFixed(2)}</dt>
        <dd>
          <LogScaleRange
            value={gamma}
            min={-10}
            max={20}
            onInput={v => setParams({ ...params, gamma: v })} />
        </dd>
        <dt>min = {min.toFixed(2)}</dt>
        <dd>
          <LogScaleRange
            value={min}
            min={barMinMax[0]}
            max={barMinMax[1]}
            onInput={v => setParams({ ...params, min: v })} />
        </dd>
        <dt>max = {max.toFixed(2)}</dt>
        <dd>
          <LogScaleRange
            value={max}
            min={barMinMax[0]}
            max={barMinMax[1]}
            onInput={v => setParams({ ...params, max: v })} />
        </dd>
      </dl>
      <button onClick={reset}>Reset</button>
    </div>
  )
})


const MAD2STDDEV = Math.sqrt(2 / Math.PI)


function autoBarMinMax(tileMeta: QuicklookMetadata) {
  const n = 1000
  const ccds = tileMeta.ccd_meta ?? []
  const min = Math.min(+Infinity, ...ccds.map(ccd => ccd.image_stat.median))
  const max = Math.max(-Infinity, ...ccds.map(ccd => ccd.image_stat.median))
  const maxMad = Math.max(-Infinity, ...ccds.map(ccd => ccd.image_stat.mad))
  return [min - n * maxMad, max + n * maxMad]
}


function autoMinMax(tileMeta: QuicklookMetadata) {
  const n = 1
  const ccds = tileMeta.ccd_meta ?? []
  const min = Math.min(+Infinity, ...ccds.map(ccd => ccd.image_stat).map(s => s.median - n * MAD2STDDEV * s.mad))
  const max = Math.max(-Infinity, ...ccds.map(ccd => ccd.image_stat).map(s => s.median + n * MAD2STDDEV * s.mad))
  return {
    min,
    max,
  }
}


const colorMaps = [
  'Gray',
  'Viridis',
  'Magma',
  'Inferno',
  'Plasma',
  'Cividis',
  'Rocket',
  'Mako',
  'Turbo',
] as const
