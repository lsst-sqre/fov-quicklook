import { FilterParams } from "./FilterParams"

type VisitEntryPropsProps = {
  style?: React.CSSProperties
}

export function ViewerSettings({ style }: VisitEntryPropsProps) {
  return (
    <div style={style}>
      <FilterParams />
    </div>
  )
}
