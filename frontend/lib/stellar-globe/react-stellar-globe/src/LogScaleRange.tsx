import { CSSProperties, memo, useCallback, useMemo } from 'react'

interface LogScaleRangeProps {
  min: number
  max: number
  value: number
  onInput: (value: number) => void
  a?: number
  nStep?: number
  className?: string
  style?: CSSProperties
}

export const LogScaleRange = memo(function LogScaleRange({
  min,
  max,
  a = 1,
  nStep = 10000,
  value,
  onInput,
  className,
  style,
}: LogScaleRangeProps) {
  const f = (x: number) => {
    return Math.sinh(a * x) / Math.sinh(a)
  }

  const g = useCallback((y: number) => {
    return Math.asinh(y * Math.sinh(a)) / a
  }, [a])

  const xMin = useMemo(() => g(min), [g, min])
  const xMax = useMemo(() => g(max), [g, max])

  const sliderValue = useMemo(() => {
    const x = g(value)
    const r = (x - xMin) / (xMax - xMin)
    const v = r * nStep
    return v
  }, [g, nStep, value, xMax, xMin])

  const handleSliderChange = (v: number) => {
    const r = v / nStep
    const x = xMin + r * (xMax - xMin)
    onInput(f(x))
  }

  return (
    <input
      type="range"
      min={0}
      max={nStep}
      step={1}
      value={sliderValue}
      onChange={e => handleSliderChange(Number(e.target.value))}
      className={className}
      style={style}
    />
  )
})