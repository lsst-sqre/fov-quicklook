import toast from 'react-hot-toast'

type CopyOptions = {
  showToast?: boolean
}

export async function copyTextToClipboard(text: string, options: CopyOptions = { showToast: true }): Promise<void> {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      console.log('Text copied to clipboard successfully!')
    } else {
      await fallbackCopyTextToClipboard(text)
    }
    if (options.showToast) {
      toast.success('Text copied to clipboard', {
        icon: '📋',
        style: {
          background: 'rgba(31, 31, 31, 0.75)',
          color: '#fff',
          boxShadow: '0 0 10px rgba(255, 255, 255, 0.5)',
        }
      })
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

