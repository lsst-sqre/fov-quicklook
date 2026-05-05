import { expect } from 'vitest'
import { AssertionError } from 'chai'

interface CustomMatchers<R = unknown> {
  toBeArrayCloseTo(array: unknown[]): R
}

declare module 'vitest' {
  interface Assertion extends CustomMatchers { }
  interface AsymmetricMatchersContaining extends CustomMatchers { }
}

expect.extend({
  // @ts-ignore
  toBeArrayCloseTo: (actual: unknown[], expected: unknown[]) => {
    expect(actual.length).toBe(expected.length)
    try {
      // @ts-ignore
      actual.forEach((x, i) => expect(x).toBeCloseTo(expected[i]))
      return {
        pass: true,
      }
    }
    catch (e) {
      if (e instanceof AssertionError) {
        return {
          message: () => `${JSON.stringify(actual)} should close to ${JSON.stringify(expected)}`,
          pass: false
        }
      }
      throw e
    }
  }
})
