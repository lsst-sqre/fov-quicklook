import { applyPatch } from "fast-json-patch"
import { produce } from "immer"
import { generateJsonPatch } from '.'
import { test, expect } from 'vitest'


test("detects deep changes in a nested object using immer", () => {
  const original = { a: { b: { c: 1 } } }
  const modified = produce(original, draft => {
    draft.a.b.c = 2
    // @ts-ignore
    draft.a.newProp = "new"
  })

  const patch = generateJsonPatch(original, modified)
  expect(patch).toEqual([
    { op: "replace", path: "/a/b/c", value: 2 },
    { op: "add", path: "/a/newProp", value: "new" }
  ])
})


test("compares arrays of objects using getKey", () => {
  const original = [{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }]
  const modified = [{ id: 1, name: "Alice" }, { id: 3, name: "Charlie" }]

  const patch = generateJsonPatch(original, modified, {
    getKey: (elem) => elem.id
  })

  expect(patch).toEqual([
    {
      "op": "add",
      "path": "/1",
      "value": {
        "id": 3,
        "name": "Charlie",
      },
    },
    {
      "op": "remove",
      "path": "/2",
    },
  ])
})


// 1. ネストしているオブジェクトの比較
test("compares nested objects", () => {
  const original = { a: { b: 1 } }
  const modified = { a: { b: 2 } }
  const patch = generateJsonPatch(original, modified)
  expect(patch).toEqual([{ op: "replace", path: "/a/b", value: 2 }])
})

// 2. ネストしていないオブジェクトの比較
test("compares non-nested objects", () => {
  const original = { a: 1 }
  const modified = { a: 2 }
  const patch = generateJsonPatch(original, modified)
  expect(patch).toEqual([{ op: "replace", path: "/a", value: 2 }])
})

// 3. 配列がdeeply equalであるがObject.isでfalse
test("compares arrays that are deeply equal but not identical", () => {
  const original = [{ a: 1 }]
  const modified = [{ a: 1 }]
  const patch = generateJsonPatch(original, modified)
  expect(patch).toEqual([
    {
      "op": "replace",
      "path": "",
      "value": [
        {
          "a": 1,
        },
      ],
    },
  ])
})

// 4. オブジェクトがdeeply equalであるがObject.isでfalse
test("compares objects that are deeply equal but not identical", () => {
  const original = { a: { b: 1 } }
  const modified = { a: { b: 1 } }
  const patch = generateJsonPatch(original, modified)
  expect(patch).toEqual([])
})

// 5. getKeyを使う
test("uses getKey for comparing arrays of objects", () => {
  const original = [{ id: 1, name: "Alice" }]
  const modified = [{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }]
  const patch = generateJsonPatch(original, modified, { getKey: (elem) => elem.id })
  expect(patch).toEqual([{ op: "add", path: "/1", value: { id: 2, name: "Bob" } }])
})

// 6. getKeyを使わない
test("does not use getKey for comparing arrays of objects", () => {
  const original = [{ name: "Alice" }]
  const modified = [{ name: "Alice" }, { name: "Bob" }]
  const patch = generateJsonPatch(original, modified)
  expect(patch).toEqual([
    {
      "op": "replace",
      "path": "",
      "value": [
        { "name": "Alice" },
        { "name": "Bob" },
      ],
    },
  ])
})


// immerを使いgetKeyを使う配列の比較でremoveを含む
test("uses immer to compare arrays with getKey, including remove operation", () => {
  const original = [{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }]
  const modified = produce(original, draft => {
    draft.splice(1, 1) // idが2の要素を削除
  })

  const patch = generateJsonPatch(original, modified, { getKey: (elem) => elem.id })
  expect(patch).toEqual([{ op: "remove", path: "/1" }])
})

// immerを使いgetKeyを使う配列の比較でaddを含む
test("uses immer to compare arrays with getKey, including add operation", () => {
  const original = [{ id: 1, name: "Alice" }]
  const modified = produce(original, draft => {
    draft.push({ id: 2, name: "Bob" }) // 新しい要素を追加
  })

  const patch = generateJsonPatch(original, modified, { getKey: (elem) => elem.id })
  expect(patch).toEqual([{ op: "add", path: "/1", value: { id: 2, name: "Bob" } }])
})


test("handles element reordering in an array using getKey", () => {
  const original = [
    { id: 1, name: "Alice" },
    { id: 2, name: "Bob" },
    { id: 3, name: "Charlie" }
  ]
  const modified = [
    { id: 2, name: "Bob" },
    { id: 1, name: "Alice" },
    { id: 3, name: "Charlie" }
  ]

  const patch = generateJsonPatch(original, modified, { getKey: (elem) => elem.id })
  expect(patch).toEqual([
    { op: "move", from: "/1", path: "/0" }
  ])
})


test("applies generated patch to the original object to match the modified object", () => {
  const original = [
    { id: 1, name: "Alice" },
    { id: 2, name: "Bob" },
    { id: 3, name: "Charlie" },
    { id: 4, name: "Dave" },
    { id: 5, name: "Eve" }
  ]
  const modified = [
    { id: 5, name: "Eve" },
    { id: 1, name: "Alice" },
    { id: 6, name: "Frank" },
    { id: 2, name: "Bob" }
  ] // 順番の入れ替え、要素の追加と削除を含む

  const patch = generateJsonPatch(original, modified, { getKey: (elem) => elem.id })

  const appliedResult = applyPatch(original, patch).newDocument
  expect(appliedResult).toEqual(modified)
})


test("accurately generates and applies patches for complex objects using immer", () => {
  const original = {
    user: {
      id: 1,
      name: "Alice",
      roles: [{ id: 1, role: "user" }, { id: 2, role: "admin" }],
      details: {
        age: 30,
        address: {
          city: "CityX",
          zipCode: "12345"
        }
      }
    },
    settings: {
      theme: "light",
      notifications: true
    }
  }

  const modified = produce(original, draft => {
    draft.user.details.age = 31
    draft.user.details.address.city = "CityY"
    draft.settings.theme = "dark"
    draft.settings.notifications = false
    draft.user.roles = draft.user.roles.filter(role => role.role !== "user")
    draft.user.roles.push({ id: 3, role: "editor" })
  })

  const patch = generateJsonPatch(original, modified, { getKey: (elem) => elem.id })
  const appliedResult = applyPatch(original, patch).newDocument
  expect(appliedResult).toEqual(modified)
})
