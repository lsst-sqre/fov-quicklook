import { decode } from "./decoder"
import { Hdu } from "./hdu"
import { DataType, HduDecodeOption } from "./types"


export class Fits extends Array<Hdu> {
  static DataType = DataType

  static async decode(arraybuffer: ArrayBuffer, hduDecodeOptions?: HduDecodeOption[]) {
    return await decode(arraybuffer, hduDecodeOptions)
  }

  static async fetch(url: string, hduDecodeOptions?: HduDecodeOption[]) {
    const ab = await (await fetch(url, { credentials: 'same-origin' })).arrayBuffer()
    return await this.decode(ab, hduDecodeOptions)
  }
}