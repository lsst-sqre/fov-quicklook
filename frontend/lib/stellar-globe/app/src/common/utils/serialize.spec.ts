import { describe, it, expect } from 'vitest'
import { deserialize, serialize } from './serialize'

describe('serialize and deserialize tests', () => {
  it('should correctly serialize and deserialize a simple object', () => {
    const obj = { name: 'John', age: 30 }
    const serialized = serialize(obj)
    const deserialized = deserialize(serialized)
    expect(deserialized).toEqual(obj)
  })

  it('should handle an empty object', () => {
    const obj = {}
    const serialized = serialize(obj)
    const deserialized = deserialize(serialized)
    expect(deserialized).toEqual(obj)
  })

  it('should handle complex nested objects', () => {
    const obj = {
      user: { name: 'Alice', details: { age: 25, city: 'Wonderland' } },
      hobbies: ['reading', 'chess']
    }
    const serialized = serialize(obj)
    const deserialized = deserialize(serialized)
    expect(deserialized).toEqual(obj)
  })
})
