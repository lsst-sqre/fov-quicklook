import { describe, it, expect } from 'vitest'
import { interpoateText } from './interpoateText'

describe('interpoateText', () => {
  const meta = {
    visit: { id: 'S2025:1234' },
    ccd_name: 'ccd_01',
    ccd_id: 42,
    exposure: 2025051500271,
    day_obs: 20250516
  } as any

  it('should replace %(ccd_name) and %(ccd_id)', () => {
    const template = 'CCD: %(ccd_name), ID: %(ccd_id)'
    expect(interpoateText(template, meta)).toBe('CCD: ccd_01, ID: 42')
  })

  it('should replace %(visit)', () => {
    const template = 'Visit: %(visit)'
    expect(interpoateText(template, meta)).toBe('Visit: [object Object]')
  })

  it('should replace %(dataType)', () => {
    const template = 'Type: %(dataType)'
    expect(interpoateText(template, meta)).toBe('Type: S2025')
  })

  it('should keep unknown keys as is', () => {
    const template = 'Unknown: %(foo)'
    expect(interpoateText(template, meta)).toBe('Unknown: %(foo)')
  })

  it('should format day_obs as ISO8601 date using pipe', () => {
    const template = 'Date: %(day_obs|iso8601)'
    expect(interpoateText(template, meta)).toBe('Date: 2025-05-16')
  })

  it('should extract sequence (last 5 digits) from number', () => {
    const template = 'Sequence: %(exposure|sequence)'
    expect(interpoateText(template, meta)).toBe('Sequence: 271')
  })

  it('should apply zero-padding to sequence', () => {
    const template = 'Padded: %(exposure|sequence|zeropadding(8))'
    expect(interpoateText(template, meta)).toBe('Padded: 00000271')
  })
})
