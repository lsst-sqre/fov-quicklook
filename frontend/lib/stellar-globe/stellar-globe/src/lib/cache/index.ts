type Options<K, V> = {
  maxSize: number
  onDrop?: (value: V, key: K) => void,
}


export class Cache<K, V>  {
  private readonly store = new Map<K, V>()
  private onDrop?: Options<K, V>["onDrop"]
  private maxSize: Options<K, V>["maxSize"]

  constructor(options: Options<K, V>) {
    this.maxSize = options.maxSize
    this.onDrop = options.onDrop
  }

  set(k: K, v: V) {
    if (this.store.has(k)) {
      const v0 = this.store.get(k)
      this.onDrop?.(v0!, k)
    }
    this.store.set(k, v)
    this.deleteOldItems()
    return this
  }

  peek(k: K) {
    return this.store.get(k)
  }

  get(k: K) {
    if (this.store.has(k)) {
      const v = this.store.get(k)!
      this.store.delete(k)
      this.store.set(k, v)
      return v
    }
    return
  }

  *keys() {
    for (const k of this.store.keys()) {
      yield k
    }
  }

  has(k: K) {
    return this.store.has(k)
  }

  clear() {
    if (this.onDrop) {
      for (const [k, v] of this.store) {
        this.onDrop(v, k)
      }
    }
    this.store.clear()
  }

  delete(k: K) {
    if (this.store.has(k)) {
      const v = this.store.get(k)
      this.onDrop?.(v!, k)
      this.store.delete(k)
    }
  }

  setLimit(limit: number) {
    this.maxSize = limit
    this.deleteOldItems()
  }

  get size() {
    return this.store.size
  }

  private deleteOldItems() {
    while (this.store.size > this.maxSize) {
      for (const [k, v] of this.store) {
        this.onDrop?.(v, k)
        this.store.delete(k)
        break
      }
    }
  }
}
