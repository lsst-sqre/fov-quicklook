export async function copyTextToClipboard(text: string): Promise<void> {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      console.log('Text copied to clipboard successfully!')
    } else {
      await fallbackCopyTextToClipboard(text)
    }
  } catch (error) {
    console.error('Failed to copy text: ', error)
  }
}


async function fallbackCopyTextToClipboard(text: string): Promise<void> {
  try {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'  // Prevent scrolling to bottom of page in MS Edge.
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    try {
      const successful = document.execCommand('copy')
      const msg = successful ? 'successful' : 'unsuccessful'
      console.log('Fallback: Copying text command was ' + msg)
    } catch (err) {
      console.error('Fallback: Oops, unable to copy', err)
    }

    document.body.removeChild(textArea)
  } catch (error) {
    console.error('Failed to copy text in fallback: ', error)
  }
}

