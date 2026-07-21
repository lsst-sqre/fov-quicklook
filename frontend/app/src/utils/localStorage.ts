function prefixKey(key: string) {
  return `fov-quicklook/${key}`
}


function getStorage<T>(storage: Storage, key: string): T | undefined {
  const item = storage.getItem(prefixKey(key))
  if (item === null) {
    return undefined
  }
  return JSON.parse(item)
}


function setStorage<T>(storage: Storage, key: string, value: T) {
  storage.setItem(prefixKey(key), JSON.stringify(value))
}


function makeStorageAccessor<T>(storage: Storage, key: string, defaultValue: T) {
  return {
    get: () => getStorage<T>(storage, key) ?? defaultValue,
    set: (value: T) => setStorage(storage, key, value),
    remove: () => storage.removeItem(prefixKey(key)),
  }
}


export function makeLocalStorageAccessor<T>(key: string, defaultValue: T) {
  return makeStorageAccessor(localStorage, key, defaultValue)
}


export function makeSessionStorageAccessor<T>(key: string, defaultValue: T) {
  return makeStorageAccessor(sessionStorage, key, defaultValue)
}
