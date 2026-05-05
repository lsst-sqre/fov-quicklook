/*

↓の例だけ対応できるsprintfの実装

sprintf(`${sign}%02d:%02d:%07.4f`, Math.floor(s / 3600), Math.floor(s / 60 % 60), s % 60)
sprintf('%4d | %s', n + 1, line)

↓はwindowオブジェクトに変更を行うのでテストに不向きのため自前で実装する
https://www.npmjs.com/package/sprintf-js


expect(sprintf('%4d | %s', 1, 'a')).toBe('   1 | a')
expect(sprintf('%07.4f', 1.23) === '01.2300')

**/


export function sprintf(format: string, ...args: any[]): string {
  let argIndex = 0
  const formatRegExp = /%(-)?(0)?(\d+)?(\.\d+)?([dfs])/g

  return format.replace(formatRegExp, (match, leftJustify, zeroPad, width, precision, type) => {
    if (argIndex >= args.length) return match
    let arg = args[argIndex++]
    let pad = ''
    let padLength = 0

    switch (type) {
      case 'd':
        arg = parseInt(arg).toString()
        break
      case 'f':
        arg = parseFloat(arg).toFixed(precision ? parseInt(precision.substring(1)) : 6)
        break
      case 's':
        arg = arg.toString()
        break
    }

    if (width) {
      padLength = parseInt(width) - arg.length
      pad = new Array(padLength + 1).join(zeroPad ? '0' : ' ')
    }

    if (leftJustify) {
      return arg + pad
    } else {
      return pad + arg
    }
  })
}
