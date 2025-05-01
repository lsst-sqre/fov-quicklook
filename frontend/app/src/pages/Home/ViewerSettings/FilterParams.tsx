import { memo, useCallback, useEffect, useMemo, useState } from "react"
import { RubinImageFilterParams } from "../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter"
import { QuicklookMetadata } from "../../../store/api/openapi"
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useHomeContext } from "../context"
import styles from './styles.module.scss'
import { LogScaleRange } from "../../../components/LogScaleRange"

const defaultContrastBias: [number, number] = [0.5, 0]

export const FilterParams = memo(() => {
  // contrast値が大きいほど範囲が狭くなる
  // (max - min)/mad == 1/contrast
  // (origin - (min + max)/2) / mad == bias
  //
  // min = origin - bias * mad - mad / (2 * contrast)
  // max = origin - bias * mad + mad / (2 * contrast)

  const dispatch = useAppDispatch()
  const params = useAppSelector(state => state.home.filterParams)
  const { currentQuicklook } = useHomeContext()
  const metadata = currentQuicklook.metadata
  const { min, max, colormap, scale, gamma } = params
  const [barMinMax, setBarMinMax] = useState<[number, number]>([-1, 1])
  const origin = useMemo(() => metadata ? getImageMedian(metadata) : 0, [metadata])
  const mad = useMemo(() => metadata ? getImageSigma(metadata) : 1, [metadata])
  const [[contrast, bias], setContrastBias] = useState<[number, number]>(defaultContrastBias)

  const setParams = useCallback((params: RubinImageFilterParams) => {
    dispatch(homeSlice.actions.setFilterParams(params))
  }, [dispatch])

  useEffect(() => {
    if (metadata) {
      const [min, max] = autoBarMinMax(metadata)
      setBarMinMax([min, max])
      setParams({ ...params, ...autoMinMax(metadata, contrast, bias) })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metadata])

  const reset = useCallback(() => {
    if (metadata) {
      setContrastBias(defaultContrastBias)
      setParams({ ...params, ...autoMinMax(metadata, ...defaultContrastBias), gamma: 0, colormap: 'Gray' })
    }
  }, [metadata, setParams, params])

  const handleParamChange = useCallback((newContrast: number, newBias: number) => {
    setContrastBias([newContrast, newBias])
    if (metadata) {
      setParams({ ...params, ...autoMinMax(metadata, newContrast, newBias) })
    }
  }, [metadata, params, setParams])

  const handleMinMaxChange = useCallback((newMin: number, newMax: number) => {
    setParams({ ...params, min: newMin, max: newMax })

    // minとmaxから逆算してcontrast, biasを更新
    if (metadata && mad > 0) {
      const newContrast = mad / (newMax - newMin)
      const newBias = (origin - (newMin + newMax) / 2) / mad
      setContrastBias([newContrast, newBias])
    }
  }, [metadata, origin, mad, params, setParams])

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
            origin={origin}
            a={100 / mad}
            onInput={v => handleMinMaxChange(v, max)} />
        </dd>
        <dt>max = {max.toFixed(2)}</dt>
        <dd>
          <LogScaleRange
            value={max}
            min={barMinMax[0]}
            max={barMinMax[1]}
            origin={origin}
            a={100 / mad}
            onInput={v => handleMinMaxChange(min, v)} />
        </dd>
        <dt>Contrast = {contrast.toFixed(2)}</dt>
        <dd>
          <LogScaleRange
            value={contrast}
            min={0}
            max={10}
            onInput={v => handleParamChange(v, bias)} />
        </dd>
        <dt>Bias = {bias.toFixed(2)}</dt>
        <dd>
          <LogScaleRange
            value={bias}
            min={-2}
            max={2}
            onInput={v => handleParamChange(contrast, v)} />
        </dd>
      </dl>
      <button onClick={reset}>Reset</button>
    </div>
  )
})


const MAD2STDDEV = Math.sqrt(2 / Math.PI)


function autoBarMinMax(tileMeta: QuicklookMetadata) {
  const n = 5000
  const ccds = (tileMeta.ccd_meta ?? []).filter(ccd => typeof ccd.image_stat.median === 'number')
  const min = Math.min(+Infinity, ...ccds.map(ccd => ccd.image_stat.median!))
  const max = Math.max(-Infinity, ...ccds.map(ccd => ccd.image_stat.median!))
  const maxSigma = Math.max(-Infinity, ...ccds.map(ccd => ccd.image_stat.mad!)) * MAD2STDDEV
  return [min - n * maxSigma, max + n * maxSigma]
}


function autoMinMax(tileMeta: QuicklookMetadata, contrast: number, bias: number) {
  const sigma = getImageSigma(tileMeta)
  const origin = getImageMedian(tileMeta)
  return {
    min: origin - bias * sigma - sigma / (2 * contrast),
    max: origin - bias * sigma + sigma / (2 * contrast),
  }
}

function median(arr: number[]) {
  arr = arr.slice().sort((a, b) => a - b)
  const mid = Math.floor(arr.length / 2)
  if (arr.length % 2 === 0) {
    return (arr[mid - 1] + arr[mid]) / 2
  } else {
    return arr[mid]
  }
}

function getImageMedian(tileMeta: QuicklookMetadata) {
  const ccds = (tileMeta.ccd_meta ?? []).filter(ccd => typeof ccd.image_stat.median === 'number')
  const medians = ccds.map(ccd => ccd.image_stat.median!)
  return median(medians)
}

function getImageSigma(tileMeta: QuicklookMetadata) {
  const ccds = (tileMeta.ccd_meta ?? []).filter(ccd => typeof ccd.image_stat.median === 'number')
  const minMad = Math.min(...ccds.map(ccd => ccd.image_stat.mad!))
  const maxMad = Math.max(...ccds.map(ccd => ccd.image_stat.mad!))
  const mad = Math.max(...ccds.map(ccd => ccd.image_stat.mad!))
  return (maxMad - minMad) + mad * MAD2STDDEV
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
