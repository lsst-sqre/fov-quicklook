import { describe, expect, it } from "vitest"
import { sprintf } from '~/utils/sprintf'


describe('sprintf', () => {
  it('should format', () => {
    expect(sprintf('%4d | %s', 1, 'a')).toBe('   1 | a')
    expect(sprintf('%4d | %s', 10, 'a')).toBe('  10 | a')
    expect(sprintf('%4d | %s', 100, 'a')).toBe(' 100 | a')
    expect(sprintf('%4d | %s', 1000, 'a')).toBe('1000 | a')
  })
})


