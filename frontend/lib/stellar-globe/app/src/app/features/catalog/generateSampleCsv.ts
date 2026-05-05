/*

Prompt for ChatGPT4

次のようなCSVをつくるTypeScript関数を作ってください。

* 型ヒントつき
* 次のようなCSV文字列を生成する

# object_id,ra,dec,value1,value2,color,marker_type
123,30.4,40.,a,b,#fff,diamond
124,30.5,42.4,c,d,#f0f,circle
...

* ra, dec はとある範囲ないの乱数
* value1, value2は適当なランダムな文字列
* colorは #0000 〜 #ffff の形式の乱数
  * 最後の一文字は透明度なのでfまたは7
# marker_type はつぎのどれか "circle" | "plus" | "x" | "hollowPlus" | "hollowX" | "dot" | "circledHollowPlus" | "circledHollowX" | "diamond" | "square" | "asterisk" | "hollowAsterisk" | "circledHollowAsterisk" | "triangle" | "pentagon"
* ra, decの範囲、行数、color, marker_typeカラムの有無を関数の引数から与える
  * 適当なデフォルト値もある


素晴らしいです。引数が多いのでオブジェクトで渡せるようにしてもらえますか？rowsのデフォルトは1000にしてください。

**/

type GenerateCSVOptions = {
  rows?: number
  raRange?: { min: number; max: number }
  decRange?: { min: number; max: number }
  includeColor?: boolean
  includeMarkerType?: boolean
}

export function generateCSV({
  rows = 1000,
  raRange = { min: 0, max: 360 },
  decRange = { min: -90, max: 90 },
  includeColor = false,
  includeMarkerType = false,
}: GenerateCSVOptions = {}): string {
  const markerTypes = [
    "circle", "plus", "x", "hollowPlus", "hollowX", "dot",
    "circledHollowPlus", "circledHollowX", "diamond", "square",
    "asterisk", "hollowAsterisk", "circledHollowAsterisk",
    "triangle", "pentagon"
  ]

  const randomColor = (): string => {
    const color = Math.floor(Math.random() * 0xFFFFF).toString(16).padStart(5, '0')
    const alpha = Math.random() > 0.5 ? 'f' : '7'
    return `#${color}${alpha}`
  }

  const randomString = (): string => Math.random().toString(36).substring(2, 4)

  let csv = '# object_id,ra,dec,value1,value2'
  if (includeColor) csv += ',color'
  if (includeMarkerType) csv += ',marker_type'
  csv += '\n'

  for (let i = 0; i < rows; i++) {
    const ra = String((Math.random() * (raRange.max - raRange.min) + raRange.min))
    const dec = String((Math.random() * (decRange.max - decRange.min) + decRange.min))
    const color = randomColor()
    const markerType = markerTypes[Math.floor(Math.random() * markerTypes.length)]
    const value1 = randomString()
    const value2 = randomString()
    csv += `${i},${ra},${dec},${value1},${value2}`
    if (includeColor) csv += `,${color}`
    if (includeMarkerType) csv += `,${markerType}`
    csv += '\n'
  }

  return csv
}
