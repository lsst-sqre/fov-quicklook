export function convertShortcutToSymbols(shortcut: string): string {
  // Macかどうかを判定
  const isMac = navigator.userAgent.toLowerCase().includes('mac')

  if (isMac) {
    // Mac用のシンボルに変換
    return shortcut
      .replace(/Meta\+/g, '⌘')
      .replace(/Shift\+/g, '⇧')
      .replace(/Alt\+/g, '⌥')
      .replace(/Ctrl\+/g, '⌃')
  } else {
    // Windows用の表記に変換
    return shortcut
      .replace(/Meta\+/g, 'Win+')
      .replace(/Shift\+/g, 'Shift+')
      .replace(/Alt\+/g, 'Alt+')
      .replace(/Ctrl\+/g, 'Ctrl+')
  }
}


export function normalizeShortcut(shortcut: string): string {
  // ショートカットを分割
  const keys = shortcut.split('+')

  // 修飾キーとメインキーを分離
  const modifiers = keys.filter(key => ['Meta', 'Ctrl', 'Alt', 'Shift'].includes(key))
  const mainKey = keys.find(key => !['Meta', 'Ctrl', 'Alt', 'Shift'].includes(key)) || ''

  // 修飾キーを正しい順序に並べ替え
  const sortedModifiers = [
    modifiers.includes('Meta') ? 'Meta' : '',
    modifiers.includes('Ctrl') ? 'Ctrl' : '',
    modifiers.includes('Alt') ? 'Alt' : '',
    modifiers.includes('Shift') ? 'Shift' : ''
  ].filter(key => key !== '')

  // 修飾キーとメインキーを結合して返す
  return [...sortedModifiers, mainKey].join('+')
}


export function generateShortcutFromEvent(event: KeyboardEvent): string {
  // 修飾キーをチェック
  const modifiers = []
  if (event.metaKey) modifiers.push('Meta')
  if (event.ctrlKey) modifiers.push('Ctrl')
  if (event.altKey) modifiers.push('Alt')
  if (event.shiftKey) modifiers.push('Shift')

  // キーコードから対応するキーを取得（例: 'G'）
  const key = event.key.length === 1 ? event.key.toUpperCase() : event.key

  // 修飾キーとメインキーを結合
  return [...modifiers, key].join('+')
}
