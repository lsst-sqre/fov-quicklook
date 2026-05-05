// see https://jsonpatch.com
import { JsonPatchOp, Options } from "../../../types/commTools/jsonpatch"


function compareValues(patches: JsonPatchOp[], oldValue: any, newValue: any, path: string, options: Options) {
  if (Object.is(oldValue, newValue)) {
    return
  }

  if (Array.isArray(oldValue) && Array.isArray(newValue)) {
    return compareArrays(patches, oldValue, newValue, path, options)
  }

  if (typeof oldValue === 'object' && typeof newValue === 'object') {
    return compareObjects(patches, oldValue, newValue, path, options)
  }

  patches.push({ op: "replace", path, value: newValue })
}


function compareArrays(patches: JsonPatchOp[], oldArray: any[], newArray: any[], path: string, options: Options) {
  const getKey = options.getKey
  if (
    getKey &&
    oldArray.every(e => getKey(e) != null) &&
    newArray.every(e => getKey(e) != null)
  ) {
    const oldMap = new Map(oldArray.map((e, i) => [getKey(e), { e, i }]))
    const newMap = new Map(newArray.map((e, i) => [getKey(e), { e, i }]))

    if (oldMap.size !== oldArray.length || newMap.size !== newArray.length) {
      console.error('Duplicated key', oldArray, newArray)
      throw new Error(`Dupliated key`)
    }

    [...newMap.entries()].sort(([, a], [, b]) => a.i - b.i).forEach(([k, { i: newIndex, e: newElement }]) => {
      // 新しい配列のインデックスで走査
      const newPath = `${path}/${newIndex}`
      if (oldMap.has(k)) {
        const { i: oldIndex, e: oldElement } = oldMap.get(k)!
        if (oldIndex !== newIndex) {
          patches.push({ op: 'move', from: `${path}/${oldIndex}`, path: newPath })
        }
        oldMap.delete(k)
        oldMap.forEach(v => {
          if (v.i > oldIndex) { --v.i }
        })
        compareValues(patches, oldElement, newElement, newPath, options)
      }
      else {
        // 追加
        patches.push({ op: 'add', path: newPath, value: newElement })
      }
      oldMap.forEach(v => {
        if (v.i >= newIndex) { ++v.i }
      })
    })
    // oldMapに残った分を消す
    for (let i = newMap.size + oldMap.size - 1; i >= newMap.size; --i) {
      patches.push({ op: 'remove', path: `${path}/${i}` })
    }
  }
  else {
    patches.push({ op: "replace", path, value: newArray })
  }
}


function compareObjects(patches: JsonPatchOp[], oldObj: Record<string, any>, newObj: Record<string, any>, basePath: string, options: Options) {
  for (const key in oldObj) {
    if (!(key in newObj)) {
      patches.push({ op: "remove", path: `${basePath}/${key}` })
    }
  }

  for (const key in newObj) {
    const newPath = `${basePath}/${key}`
    if (!(key in oldObj)) {
      patches.push({ op: "add", path: newPath, value: newObj[key] })
    } else {
      compareValues(patches, oldObj[key], newObj[key], newPath, options)
    }
  }
}


export function generateJsonPatch(
  oldObj: unknown,
  newObj: unknown,
  options: Options = { getKey: (elem) => elem.id }
): JsonPatchOp[] {
  const patches: JsonPatchOp[] = []
  compareValues(patches, oldObj, newObj, '', options)
  return patches
}
