export type DecodeResponse = Ok | LoadError


export type DecodeRequest = {
  id: number
  url: string
  flipY: boolean
}


type LoadError = {
  id: number
  type: 'error'
  message: string
}

type Ok = {
  id: number
  type: 'ok'
  imageBitmap: ImageBitmap
}


function main() {
  self.addEventListener('message', async (e) => {
    const { id, url, flipY } = e.data as DecodeRequest
    try {
      const response = await fetch(url, { mode: 'cors' })
      const blob = await response.blob()
      const imageBitmap = await createImageBitmap(blob, { imageOrientation: flipY ? 'flipY' : undefined })
      postMessage<DecodeResponse>({ id, type: 'ok', imageBitmap }, [imageBitmap])
    }
    catch (error) {
      postMessage<DecodeResponse>({ id, type: 'error', message: String(error) })
    }
  })
}


function postMessage<T>(data: T, transferable: any[] = []) {
  (self as any as Worker).postMessage(data, transferable)
}


main()
