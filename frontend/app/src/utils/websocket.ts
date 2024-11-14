export function websocketUrl(path: string) {
  const currentScheme = window.location.protocol // 現在のページのスキームを取得
  const webSocketScheme = currentScheme === 'https:' ? 'wss:' : 'ws:' // スキームに応じたWebSocketのスキームを選択

  // 現在のページの絶対パスを取得
  const currentPath = window.location.pathname
  const absolutePath = currentPath.substring(0, currentPath.lastIndexOf('/'))

  // WebSocketのスキーム、ホスト、絶対パス、与えられた相対URLを組み合わせてWebSocket URLを構築
  const webSocketUrl = `${webSocketScheme}//${window.location.host}${absolutePath}/${path}`

  return webSocketUrl
}
