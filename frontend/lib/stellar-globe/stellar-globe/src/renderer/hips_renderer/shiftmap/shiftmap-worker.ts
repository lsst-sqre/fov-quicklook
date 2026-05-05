import { decode_id, shiftmap } from '../healpix'
import { DELTA_MAP_N, ShiftmapRequest } from "./interface"

function main() {
  self.addEventListener('message', (e) => {
    const { id } = e.data as ShiftmapRequest
    const { order, index } = decode_id(id)
    const array = shiftmap(order, index, DELTA_MAP_N)
    const shiftmaps = [{ id, arraybuffer: array.buffer }];
    (self as any as Worker).postMessage(shiftmaps, shiftmaps.map((sm) => sm.arraybuffer))
  })
}

main()
