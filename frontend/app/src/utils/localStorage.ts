function prefixKey(key: string) {
  return `fov-quicklook/${key}`
}


function getLocalStorage<T>(key: string): T | undefined {
  const item = localStorage.getItem(prefixKey(key))
  if (item === null) {
    return undefined
  }
  return JSON.parse(item)
}


function setLocalStorage<T>(key: string, value: T) {
  localStorage.setItem(prefixKey(key), JSON.stringify(value))
}


export function makeLocalStorageAccessor<T>(key: string, defaultValue: T) {
  return {
    get: () => getLocalStorage<T>(key) ?? defaultValue,
    set: (value: T) => setLocalStorage(key, value),
    remove: () => localStorage.removeItem(prefixKey(key)),
  }
}
