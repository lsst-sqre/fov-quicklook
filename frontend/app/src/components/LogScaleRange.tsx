import { CSSProperties, memo, useCallback, useMemo } from 'react'

interface LogScaleRangeProps {
  min: number
  max: number
  value: number
  onInput: (value: number) => void
  origin?: number
  a?: number
  nStep?: number
  className?: string
  style?: CSSProperties
}

export const LogScaleRange = memo(function LogScaleRange({
  min,
  max,
  origin = 0,
  a = 1,
  nStep = 10000,
  value,
  onInput,
  className,
  style,
}: LogScaleRangeProps) {
  // 関数f, gを使いスライダーの値を変換する
  //
  // y = f(x)
  // x = g(y) の関係にある
  //
  // xの範囲は[xMin, xMax]
  // yの範囲は[min, max]
  
  const f = (x: number) => {
    // aはスケールの大きさを決めるパラメータ
    // aが大きいほどorigin周りでxに対して急激に変化する
    return Math.sinh(a * (x - origin)) / Math.sinh(a) + origin
  }

  const g = useCallback((y: number) => {
    return Math.asinh((y - origin) * Math.sinh(a)) / a + origin
  }, [a, origin])

  const xMin = useMemo(() => g(min), [g, min])
  const xMax = useMemo(() => g(max), [g, max])

  const sliderValue = useMemo(() => {
    const x = g(value)
    const r = (x - xMin) / (xMax - xMin)
    const v = r * nStep
    return v
  }, [g, nStep, value, xMax, xMin])

  const handleSliderChange = (v: number) => {
    const r = v / nStep // [0, 1]
    const x = xMin + r * (xMax - xMin) // [xMin, xMax]
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