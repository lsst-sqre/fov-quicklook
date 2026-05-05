import { CSSProperties } from "react"

export type Size = {
  width: number
  height: number
}

export type PartialSize = Partial<Size>

type PositionX = { left: number } | { right: number }
type PositionY = { top: number } | { bottom: number }

export type TopLeft = {
  left: number
  top: number
}

export type Position = PositionX & PositionY
export type Rect = TopLeft & Size

export type Origin = { x: 'left' | 'right', y: 'top' | 'bottom' }

export type CSSPosition = Pick<CSSProperties, 'top' | 'left' | 'right' | 'bottom'>
export type CSSSize = Pick<CSSProperties, 'width' | 'height'>
export type CSSSizeLimit = Pick<CSSProperties, 'minWidth' | 'maxWidth' | 'minHeight' | 'maxHeight'>
