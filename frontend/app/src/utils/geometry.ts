import { V2 } from "@stellar-globe/stellar-globe"


export function includedInPolygon(p: V2, polygon: V2[]): boolean {
  function edge(p1: V2, p2: V2): V2 {
    return [p2[0] - p1[0], p2[1] - p1[1]]
  }
  function cross(v1: V2, v2: V2): number {
    return v1[0] * v2[1] - v1[1] * v2[0]
  }

  for (let i = 0; i < polygon.length; i++) {
    const p1 = polygon[i]
    const p2 = polygon[(i + 1) % polygon.length]
    const edgeVec = edge(p1, p2)
    const pointVec = edge(p1, p)
    if (cross(edgeVec, pointVec) < 0) {
      return false
    }
  }

  return true
}


// export function mean(a: number[]) {
//   return a.reduce((acc, v) => acc + v, 0) / a.length
// }
