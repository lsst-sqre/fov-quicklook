export async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  }
  catch {
    console.warn('Failed to copy to clipboard')
  }
}
