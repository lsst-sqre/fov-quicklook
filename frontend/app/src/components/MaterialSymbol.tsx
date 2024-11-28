import { MaterialSymbol as MaterialSymbolType } from 'material-symbols'

type Props = {
  symbol: MaterialSymbolType
}

export function MaterialSymbol({ symbol }: Props) {
  return <span className="material-symbols-rounded">{symbol}</span>
}
