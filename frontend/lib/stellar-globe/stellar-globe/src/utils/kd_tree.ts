// @ts-ignore
type Coord<N> = number[]

interface ITreeNode<N, V> {
  coord: Coord<N>
  value: V
  left?: ITreeNode<N, V>
  right?: ITreeNode<N, V>
}

type Metric<N, V> = (value: V) => Coord<N>

export class KdTree<N, V> {
  readonly n: number
  readonly size: number
  private readonly root: ITreeNode<N, V> | undefined

  constructor(values: V[], private value2coord: Metric<N, V>) {
    this.n = values.length === 0 ? -1 : value2coord(values[0]).length
    this.size = values.length
    this.root = this.constructTree(values.slice(), 0)!
  }

  private constructTree(values: V[], dimension: number): ITreeNode<N, V> | undefined {
    if (values.length === 0) {
      return undefined
    }
    const v2c = this.value2coord
    const i = dimension % this.n
    values.sort((a, b) => v2c(a)[i] - v2c(b)[i])
    const middleIndex = Math.floor(values.length / 2)
    const middleValue = values[middleIndex]
    return {
      coord: v2c(middleValue),
      value: middleValue,
      left: this.constructTree(values.slice(0, middleIndex), i + 1),
      right: this.constructTree(values.slice(middleIndex + 1), i + 1),
    }
  }

  nearest(coord: Coord<N>, maxCount: number = 1, maxDistance = Infinity) {
    if (!this.root) {
      return []
    }
    const results: Array<{ value: V, d2: number }> = []
    this.dig(results, coord, this.root, 0, maxCount, maxDistance)
    return results.map((r) => r.value)
  }

  // tslint:disable-next-line:cyclomatic-complexity
  private dig(
    results: Array<{ value: V, d2: number }>,
    coord: Coord<N>, node: ITreeNode<N, V>, dimension: number, maxCount: number, maxDistance: number,
  ) {
    const i = dimension % this.n

    const d2 = distance2(coord, node.coord)
    if (d2 <= maxDistance * maxDistance) {
      let j = 0
      for (j = 0; j < results.length; ++j) {
        if (d2 <= results[j].d2) {
          break
        }
      }
      if (j < maxCount) {
        results.splice(j, 0, { d2, value: node.value })
        results.splice(maxCount)
        if (results.length === maxCount) {
          maxDistance = Math.sqrt(results[results.length - 1].d2)
        }
      }
    }

    if (coord[i] < node.coord[i]) {
      if (node.left) {
        this.dig(results, coord, node.left, i + 1, maxCount, maxDistance)
      }
      if (node.right && node.coord[i] - coord[i] < maxDistance) {
        this.dig(results, coord, node.right, i + 1, maxCount, maxDistance)
      }
    } else {
      if (node.left && coord[i] - node.coord[i] <= maxDistance) {
        this.dig(results, coord, node.left, i + 1, maxCount, maxDistance)
      }
      if (node.right) {
        this.dig(results, coord, node.right, i + 1, maxCount, maxDistance)
      }
    }
  }
}

function distance2<N>(a: Coord<N>, b: Coord<N>) {
  let d2 = 0
  for (let i = 0; i < a.length; ++i) {
    const d = a[i] - b[i]
    d2 += d * d
  }
  return d2
}
