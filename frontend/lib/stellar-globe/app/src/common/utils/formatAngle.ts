export type AngleUnit = 'radian' | 'degree' | 'sexadecimal'


export function formatAngleInSexagesimal(radians: number): string {
  // 1ラジアンを度に変換
  const degrees = radians * 180 / Math.PI

  // 1度以上の場合、度で表示
  if (degrees >= 1) {
    return degrees.toFixed(3) + "°"
  }

  // 秒単位に変換
  const secondsTotal = degrees * 3600

  // 1分以上1度未満の場合、分と秒で表示
  if (secondsTotal >= 60) {
    const minutes = Math.floor(secondsTotal / 60)
    const seconds = secondsTotal % 60
    return `${minutes}' ${seconds.toFixed(1)}''`
  }

  // 1秒以下の場合、有効数字3桁で秒を表示
  if (secondsTotal <= 1) {
    return secondsTotal.toPrecision(3) + "''"
  }

  // 1分未満で1秒以上の場合、秒で表示
  return secondsTotal.toPrecision(3) + "''"
}


export function formatAngle(radians: number, unit: AngleUnit) {
  switch (unit) {
    case 'sexadecimal':
      return formatAngleInSexagesimal(radians)
    case 'radian':
      return radians.toPrecision(3)
    case 'degree':
      return (radians / Math.PI * 180).toPrecision(3)
  }
}
