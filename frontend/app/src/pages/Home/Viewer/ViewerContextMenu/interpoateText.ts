import { DataSourceCcdMetadata } from "../../../../store/api/openapi"

// パイプライン処理のマップ
type PipeHandler = {
  [key: string]: (val: number, ...args: any[]) => any
}

const pipeHandlers: PipeHandler = {
  iso8601: (val: number): string => {
    const dateStr = val.toString()
    const year = dateStr.substring(0, 4)
    const month = dateStr.substring(4, 6)
    const day = dateStr.substring(6, 8)
    return `${year}-${month}-${day}`
  },
  sequence: (val: number): number => {
    return val % 100000
  },
  zeropadding: (val: number, width: number): string => {
    return val.toString().padStart(width, '0')
  }
}

export function interpoateText(template: string, meta: DataSourceCcdMetadata): string {
  /*
  metaには↓が含まれる
    ccd_name: string;
    ccd_id: number;
    exposure: number;
    day_obs: number;
    uuid: string;

  この関数は、templateの中に%(visit)や%(ccd_id)が含まれている場合、それをmetaの値に置き換える
  例:
  template = '%(uuid)'
  meta = { uuid: '1234' }
  interpoateText(template, meta) => '1234'
  
  template = "{'exposure': %(exposure), 'detector': %(detector)}"
  meta = { exposure: 100.5, detector: 'detector_01' }
  interpoateText(template, meta) => "{'exposure': 100.5, 'detector': %(detector)}"
  
  またパイプ機能があり
  %(day_obs|iso8601) → 2025-05-16
  のような置き換えができる
  
  `sequence`は整数の下５桁(%100000)を取得する
  例えば`exposure = 2025051500271`のとき
  %(exposure|sequence) → 271

  `zeropadding(8)`は整数を8桁にゼロパディングする
  例えば`exposure = 123`のとき
  %(exposure|sequence|zeropadding(8)) → 00000123

  */
  type Meta2 = DataSourceCcdMetadata & {
    dataType: string
  }

  const meta2 = { ...meta } as Meta2
  meta2.dataType = meta.visit.id.split(':')[0]

  return template.replace(/%\((\w+(?:\|\w+(?:\(\d+\))?)*)\)/g, (match, expr) => {
    const [key, ...pipes] = expr.split('|')

    if (!(key in meta2)) {
      return match
    }

    let value: any = meta2[key as keyof Meta2]

    // パイプライン処理を適用
    for (const pipe of pipes) {
      const pipeMatch = pipe.match(/(\w+)(?:\((\d+)\))?/)
      if (!pipeMatch) continue

      const [, pipeName, pipeArg] = pipeMatch

      if (pipeName in pipeHandlers && typeof value === 'number') {
        const args = pipeArg ? [parseInt(pipeArg, 10)] : []
        value = pipeHandlers[pipeName](value, ...args)
      }
    }

    return `${value}`
  })
}
