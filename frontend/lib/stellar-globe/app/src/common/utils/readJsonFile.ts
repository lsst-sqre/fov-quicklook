export async function readJsonFile(file: File) {
  return new Promise<any>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        resolve(JSON.parse(e.target?.result as string))
      }
      catch (e) {
        reject(e)
      }
    }
    reader.readAsText(file)
  })
}
