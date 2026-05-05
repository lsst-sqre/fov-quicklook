// memoizeOne.test.ts
import { describe, expect, it } from 'vitest'

import { memoizeOne } from './memoizeOne'

describe('memoizeOne', () => {
  it('should use cached value for the same arguments', () => {
    let computationCount = 0
    const fn = (x: number, y: number) => {
      computationCount++
      return x + y
    }
    const memoizedFn = memoizeOne(fn)

    memoizedFn(1, 2) // 初回計算
    memoizedFn(1, 2) // キャッシュされた値を使用

    expect(computationCount).toBe(1) // 計算は1回だけ行われるべき
  })

  it('should compute new value for different arguments', () => {
    let computationCount = 0
    const fn = (x: number, y: number) => {
      computationCount++
      return x + y
    }
    const memoizedFn = memoizeOne(fn)

    memoizedFn(1, 2) // 初回計算
    memoizedFn(2, 3) // 新しい引数で計算

    expect(computationCount).toBe(2) // 計算は2回行われるべき
  })
})
