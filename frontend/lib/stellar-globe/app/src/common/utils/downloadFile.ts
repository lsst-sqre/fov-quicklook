type Params = {
  content: string
  type: string
  filename: string
}


export function downloadFile({ content, filename, type }: Params) {
  // Blobオブジェクトを作成
  const blob = new Blob([content], { type })

  // Blobからダウンロード用のURLを作成
  const url = window.URL.createObjectURL(blob)

  // a要素を作成してダウンロードを実行
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()

  // 後処理
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}


export function downloadJson({ content, filename }: { content: unknown, filename: string }) {
  return downloadFile({ content: JSON.stringify(content, undefined, 2), filename, type: 'application/json' })
}
