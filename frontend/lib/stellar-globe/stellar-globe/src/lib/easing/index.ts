export function linear(x: number) {
  return x
}

export function slowStart2(x: number) {
  return x * x
}

export function fastStart2(x: number) {
  x = 1 - x
  return 1 - x * x
}

export function slowStart4(x: number) {
  const y = x * x
  return y * y
}

export function fastStart4(x: number) {
  x = 1 - x
  const y = x * x
  return 1 - y * y
}

export function slowStartStop2(x: number) {
  const x2 = 1 - x
  return x < 0.5 ? 2 * x * x : -2 * x2 * x2 + 1
}

export function slowStartStop4(x: number) {
  const y = x * x
  const x2 = 1 - x
  const y2 = x2 * x2
  return x < 0.5 ? 8 * y * y : -8 * y2 * y2 + 1
}
