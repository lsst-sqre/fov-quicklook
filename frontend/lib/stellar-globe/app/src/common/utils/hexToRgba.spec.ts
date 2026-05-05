import { describe, expect, it } from 'vitest'
import { hexToRgba } from './hexToRgba'

describe('hexToRgba', () => {
  it('should convert #RGB format correctly', () => {
    expect(hexToRgba('#f0f')).toEqual([1, 0, 1, 1])
  })

  it('should convert #RGBA format correctly', () => {
    expect(hexToRgba('#f0ff')).toEqual([1, 0, 1, 1])
  })

  it('should convert #RRGGBB format correctly', () => {
    expect(hexToRgba('#ff00ff')).toEqual([1, 0, 1, 1])
  })

  it('should convert #RRGGBBAA format correctly', () => {
    expect(hexToRgba('#ff00ffff')).toEqual([1, 0, 1, 1])
  })

  it('should throw an error for invalid format', () => {
    expect(() => hexToRgba('f0f')).toThrow("Invalid format: Hex color should start with '#'")
    expect(() => hexToRgba('#f0fg')).toThrow("Invalid hex color value")
  })
})
