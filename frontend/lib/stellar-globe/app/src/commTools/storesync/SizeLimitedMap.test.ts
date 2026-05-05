import { test } from 'vitest'
import { SizeLimitedMap } from './SizeLimitedMap'

test("should set and get values correctly", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")
  map.set(3, "three")

  expect(map.get(1)).toBe("one")
  expect(map.get(2)).toBe("two")
  expect(map.get(3)).toBe("three")
})

test("should return undefined for non-existent keys", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")

  expect(map.get(3)).toBeUndefined()
})

test("should update values correctly", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")
  map.set(3, "three")

  map.set(2, "new two")

  expect(map.get(2)).toBe("new two")
})

test("should check if key exists correctly", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")

  expect(map.has(1)).toBe(true)
  expect(map.has(3)).toBe(false)
})

test("should limit the size of the map", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")
  map.set(3, "three")
  map.set(4, "four")

  expect(map.has(1)).toBe(false)
  expect(map.has(2)).toBe(true)
  expect(map.has(3)).toBe(true)
  expect(map.has(4)).toBe(true)
})
test("should return the correct size", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")
  map.set(3, "three")

  expect(map.size).toBe(3)
})

test("should return the correct size after adding and updating values", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")
  map.set(3, "three")

  map.set(2, "new two")
  map.set(4, "four")

  expect(map.size).toBe(3)
})

test("should return the correct size after removing values", () => {
  const map = new SizeLimitedMap<number, string>(3)
  map.set(1, "one")
  map.set(2, "two")
  map.set(3, "three")

  map.delete(2)

  expect(map.size).toBe(2)
})