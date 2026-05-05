// rounding.test.ts
import { roundToPrecision } from './roundToPrecision'
import { describe, it, expect } from 'vitest'

describe('roundToPrecision', () => {
  it('should round to the nearest integer when precision is 0', () => {
    expect(roundToPrecision(1.5, 0)).toBe(2)
    expect(roundToPrecision(1.4, 0)).toBe(1)
  })

  it('should round to the specified number of decimal places', () => {
    expect(roundToPrecision(1.2345, 2)).toBe(1.23)
    expect(roundToPrecision(1.0051, 2)).toBe(1.01)
  })

  it('should handle rounding for negative numbers', () => {
    expect(roundToPrecision(-1.2345, 2)).toBe(-1.23)
    expect(roundToPrecision(-1.005, 2)).toBe(-1.0)
  })

  it('should not change the number if the specified precision is higher than the number of decimals', () => {
    expect(roundToPrecision(1.234, 5)).toBe(1.234)
  })
})
