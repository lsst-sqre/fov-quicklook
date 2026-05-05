import { MaterialSymbol } from 'material-symbols'
import { HTMLAttributes } from 'react'

type Props = {
  type: MaterialSymbol
  marginRight?: boolean
  marginLeft?: boolean
} & HTMLAttributes<HTMLSpanElement>


export function Icon({ type, marginLeft, marginRight, style, ...rests }: Props) {
  return (
    <span className="material-symbols-outlined" style={
      {
        display: 'flex',
        justifyContent: 'center',
        ...style,
        ...(marginLeft && { marginLeft: '0.5em' }),
        ...(marginRight && { marginRight: '0.5em' }),
      }} {...rests}>{type}</span>
  )
}
