import { Globe } from '@stellar-globe/stellar-globe'
import { ReactNode, forwardRef, useEffect, useImperativeHandle } from "react"
import { GlobeContext, GlobeHooks, GlobeOptions, setDisplayName, useGenerateContext } from './GlobeContext'


export type GlobeHandle = () => Globe
type GlobeProps = GlobeOptions & GlobeHooks & {
  children?: ReactNode
}


export const Globe$ = forwardRef<GlobeHandle, GlobeProps>(function Globe$(
  {
    children,
    ...props
  }: GlobeProps,
  ref
) {
  const context = useGenerateContext(props)
  const { containerRef, state: { globe } } = context

  useImperativeHandle(ref, () => () => context.state.globe!, [context.state])

  useEffect(() => {
    globe?.layerSorter.sort()
  })

  return (
    <GlobeContext.Provider value={context}>
      <div ref={containerRef} style={{ height: '100%', position: 'relative' }} >
        {children}
        {/* ここにcanvasができる */}
      </div>
    </GlobeContext.Provider>
  )
})

setDisplayName({ Globe$ })
