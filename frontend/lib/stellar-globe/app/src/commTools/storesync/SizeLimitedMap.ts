export class SizeLimitedMap<K, V> {
  private map = new Map<K, V>();
  private _maxSize: number

  constructor(maxSize: number) {
    this._maxSize = maxSize
  }

  get maxSize() {
    return this._maxSize
  }

  set maxSize(value: number) {
    this._maxSize = value
    if (this.map.size > this._maxSize) {
      this.map.delete(this.map.keys().next().value!)
    }
  }

  set(key: K, value: V) {
    this.map.set(key, value)
    this.maxSize = this._maxSize
  }

  get(key: K) {
    return this.map.get(key)
  }

  has(key: K) {
    return this.map.has(key)
  }

  get size() {
    return this.map.size
  }

  delete(key: K) {
    return this.map.delete(key)
  }

  clear() {
    this.map.clear()
  }
}
