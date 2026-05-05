import { describe, it, expect } from 'vitest'
import { Cache } from '~/lib/cache'


describe('CacheMap', () => {
  it('test1', () => {
    const dropLog: number[] = []
    const m = new Cache<string, number>({ maxSize: 3, onDrop: v => dropLog.push(v) })

    m.set('one', 1)
    m.set('two', 2)
    m.set('three', 3)
    expect(m.get('one')).toBe(1)
    expect(m.get('two')).toBe(2)
    expect(m.get('three')).toBe(3)

    m.set('four', 4)
    expect(m.get('four')).toBe(4)
    expect(m.get('one')).toBe(undefined)
    expect(m.get('two')).toBe(2)
    m.set('five', 5)
    expect(m.peek('two')).toBe(2)
    expect(m.peek('three')).toBe(undefined)

    expect(m.size).toBe(3)
    expect(dropLog).toEqual([1, 3])

    m.clear()
    expect(m.size).toBe(0)
    expect(dropLog).toEqual([1, 3, 4, 2, 5])

    m.set('one', 1)
    m.set('two', 2)

    expect(new Set(m.keys())).toEqual(new Set(['one', 'two']))

    m.delete('one')
    expect(m.get('one')).toBe(undefined)
    expect(m.size).toBe(1)
    expect(new Set(m.keys())).toEqual(new Set(['two']))
  })
})
