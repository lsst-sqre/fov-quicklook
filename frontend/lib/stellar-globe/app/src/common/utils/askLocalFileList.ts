type Options = {
  multiple?: boolean
}


export function askLocalFileList({
  multiple = false,
}: Options = {}): Promise<FileList> {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = multiple
    input.style.display = 'none'

    input.onchange = () => {
      if (input.files && input.files.length > 0) {
        resolve(input.files)
      } else {
        reject(new Error('No files selected'))
      }
      // Remove input from DOM after selection
      document.body.removeChild(input)
    }

    document.body.appendChild(input)
    input.click()
  })
}
