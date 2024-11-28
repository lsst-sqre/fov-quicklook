export async function copyTextToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    console.log('Text copied to clipboard successfully!')
  } catch (error) {
    console.error('Failed to copy text: ', error)
  }
}
