export function cropCanvasToAspectRatio(originalCanvas: HTMLCanvasElement, targetAspectRatio: number) {
  // 元のキャンバスの幅と高さを取得
  var originalWidth = originalCanvas.width
  var originalHeight = originalCanvas.height
  var originalAspectRatio = originalWidth / originalHeight

  var targetWidth, targetHeight

  // 元のアスペクト比と目的のアスペクト比を比較して、切り出しサイズを決定
  if (originalAspectRatio > targetAspectRatio) {
    // 元のアスペクト比が目的のアスペクト比より大きい場合、高さを基準に幅を調整
    targetHeight = originalHeight
    targetWidth = targetHeight * targetAspectRatio
  } else {
    // 元のアスペクト比が目的のアスペクト比より小さいか等しい場合、幅を基準に高さを調整
    targetWidth = originalWidth
    targetHeight = targetWidth / targetAspectRatio
  }

  // 新しいキャンバス要素を作成
  var croppedCanvas = document.createElement('canvas')
  var croppedCtx = croppedCanvas.getContext('2d')

  if (croppedCtx === null) {
    throw new Error(`Failed to croppedCtx.getContext("2d")`)
  }

  // 新しいキャンバスのサイズを切り出しサイズに設定
  croppedCanvas.width = targetWidth
  croppedCanvas.height = targetHeight

  // 元のキャンバスの中心から切り出しサイズ分を新しいキャンバスに描画
  croppedCtx.drawImage(originalCanvas, (originalWidth - targetWidth) / 2, (originalHeight - targetHeight) / 2, targetWidth, targetHeight, 0, 0, targetWidth, targetHeight)

  // 新しいキャンバスの内容をDataURLに変換して返す
  return croppedCanvas
}
