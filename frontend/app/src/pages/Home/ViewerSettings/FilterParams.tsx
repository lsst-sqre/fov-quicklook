import { memo, useCallback, useEffect, useMemo, useState } from "react"
import { RubinImageFilterParams } from "../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter"
import { QuicklookMetadata } from "../../../store/api/openapi"
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useHomeContext } from "../context"
import styles from './styles.module.scss'
import { LogScaleRange } from "../../../components/LogScaleRange"
import { initialSearchParams } from "../../../hooks/useHashSync"

const defaultContrastBias: [number, number] = [0.5, 0]

export const FilterParams = memo(() => {
  const dispatch = useAppDispatch()
  const params = useAppSelector(state => state.home.filterParams)
  const { currentQuicklook } = useHomeContext()
  const metadata = currentQuicklook.metadata
  const { min, max, colormap, scale, gamma } = params
  const [barMinMax, setBarMinMax] = useState<[number, number]>([-1, 1])
  const origin = useMemo(() => metadata ? getImageMedian(metadata) : 0, [metadata])
  const mad = useMemo(() => metadata ? getImageSigma(metadata) : 1, [metadata])
  const [[contrast, bias], setContrastBias] = useState<[number, number]>(defaultContrastBias)
  const [showTextInputs, setShowTextInputs] = useState(false)

  const setParams = useCallback((params: RubinImageFilterParams) => {
    dispatch(homeSlice.actions.setFilterParams(params))
  }, [dispatch])

  useEffect(() => {
    if (metadata) {
      const [min, max] = autoBarMinMax(metadata)
      setBarMinMax([min, max])
      const shouldDoAutoMinMax = currentQuicklook.changeCount() > 1 || initialSearchParams.filterParams === undefined
      if (shouldDoAutoMinMax) {
        setParams({ ...params, ...autoMinMax(metadata, contrast, bias) })
      }
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
      </dl>

      <FilterParamSliders
        params={params}
        min={min}
        max={max}
        gamma={gamma}
        contrast={contrast}
        bias={bias}
        barMinMax={barMinMax}
        origin={origin}
        mad={mad}
        onGammaChange={v => setParams({ ...params, gamma: v })}
        onMinMaxChange={handleMinMaxChange}
        onContrastBiasChange={handleParamChange}
      />

      {showTextInputs && (
        <FilterParamTextInputs
          gamma={gamma}
          min={min}
          max={max}
          contrast={contrast}
          bias={bias}
          onGammaChange={v => setParams({ ...params, gamma: v })}
          onMinMaxChange={handleMinMaxChange}
          onContrastBiasChange={handleParamChange}
        />
      )}

      <button onClick={reset}>Reset</button>
      <button onClick={() => setShowTextInputs(prev => !prev)}>{showTextInputs ? 'Hide' : 'Show'} Text Inputs</button>
    </div>
  )
})

type FilterParamSlidersProps = {
  params: RubinImageFilterParams
  min: number
  max: number
  gamma: number
  contrast: number
  bias: number
  barMinMax: [number, number]
  origin: number
  mad: number
  onGammaChange: (v: number) => void
  onMinMaxChange: (min: number, max: number) => void
  onContrastBiasChange: (contrast: number, bias: number) => void
}

const FilterParamSliders = memo(({
  min,
  max,
  gamma,
  contrast,
  bias,
  barMinMax,
  origin,
  mad,
  onGammaChange,
  onMinMaxChange,
  onContrastBiasChange
}: FilterParamSlidersProps) => {
  return (
    <dl>
      <dt>gamma = {gamma.toFixed(2)}</dt>
      <dd>
        <LogScaleRange
          value={gamma}
          min={-10}
          max={20}
          onInput={onGammaChange} />
      </dd>
      <dt>min = {min.toFixed(2)}</dt>
      <dd>
        <LogScaleRange
          value={min}
          min={barMinMax[0]}
          max={barMinMax[1]}
          origin={origin}
          a={100 / mad}
          onInput={v => onMinMaxChange(v, max)} />
      </dd>
      <dt>max = {max.toFixed(2)}</dt>
      <dd>
        <LogScaleRange
          value={max}
          min={barMinMax[0]}
          max={barMinMax[1]}
          origin={origin}
          a={100 / mad}
          onInput={v => onMinMaxChange(min, v)} />
      </dd>
      <dt>Contrast = {contrast.toFixed(2)}</dt>
      <dd>
        <LogScaleRange
          value={contrast}
          min={0}
          max={10}
          onInput={v => onContrastBiasChange(v, bias)} />
      </dd>
      <dt>Bias = {bias.toFixed(2)}</dt>
      <dd>
        <LogScaleRange
          value={bias}
          min={-2}
          max={2}
          onInput={v => onContrastBiasChange(contrast, v)} />
      </dd>
    </dl>
  )
})

type FilterParamTextInputsProps = {
  gamma: number
  min: number
  max: number
  contrast: number
  bias: number
  onGammaChange: (v: number) => void
  onMinMaxChange: (min: number, max: number) => void
  onContrastBiasChange: (contrast: number, bias: number) => void
}

const FilterParamTextInputs = memo(({
  gamma,
  min,
  max,
  contrast,
  bias,
  onGammaChange,
  onMinMaxChange,
  onContrastBiasChange
}: FilterParamTextInputsProps) => {
  return (
    <div className={styles.textInputs}>
      <dl>
        <dt>Gamma</dt>
        <dd>
          <input
            type="number"
            value={gamma}
            step="0.1"
            onChange={e => onGammaChange(Number(e.target.value))}
          />
        </dd>
        <dt>Min</dt>
        <dd>
          <input
            type="number"
            value={min}
            step="0.1"
            onChange={e => onMinMaxChange(Number(e.target.value), max)}
          />
        </dd>
        <dt>Max</dt>
        <dd>
          <input
            type="number"
            value={max}
            step="0.1"
            onChange={e => onMinMaxChange(min, Number(e.target.value))}
          />
        </dd>
        <dt>Contrast</dt>
        <dd>
          <input
            type="number"
            value={contrast}
            step="0.1"
            min="0"
            onChange={e => onContrastBiasChange(Number(e.target.value), bias)}
          />
        </dd>
        <dt>Bias</dt>
        <dd>
          <input
            type="number"
            value={bias}
            step="0.1"
            onChange={e => onContrastBiasChange(contrast, Number(e.target.value))}
          />
        </dd>
      </dl>
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
