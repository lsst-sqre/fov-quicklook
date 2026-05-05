import { CSSPosition, Origin, Position, Size, TopLeft } from './types'


export function position2topleft(p: Position, size: Size): TopLeft {
  const { innerWidth, innerHeight } = window
  const { width, height } = size
  return pickXY(p, ([[xkey, xvalue], [ykey, yvalue]]) => {
    const left = xkey === 'left' ? xvalue : innerWidth - xvalue - width
    const top = ykey === 'top' ? yvalue : innerHeight - yvalue - height
    return {
      left, top,
    }
  })
}


export function pickXY<T>(p: Position, cb: (xy: [['left' | 'right', number], ['top' | 'bottom', number]]) => T): T {
  return cb([
    'left' in p ? ['left', p.left] : ['right', p.right],
    'top' in p ? ['top', p.top] : ['bottom', p.bottom],
  ])
}


export function position2origin(p: Position | CSSPosition): Origin {
  return {
    x: 'left' in p ? 'left' : 'right',
    y: 'top' in p ? 'top' : 'bottom',
  }
}


export function convertOrigin(p: Position, s: Size, o: Origin): Position {
  const W = window.innerWidth
  const H = window.innerHeight
  return {
    [o.x]:
      o.x === 'left' ? (
        'left' in p ? p.left : p.right - s.width
      ) : (
        'right' in p ? p.right : W - (p.left + s.width)
      ),
    [o.y]:
      o.y === 'top' ? (
        'top' in p ? p.top : p.bottom - s.height
      ) : (
        'bottom' in p ? p.bottom : H - (p.top + s.height)
      )
  } as Position
}
