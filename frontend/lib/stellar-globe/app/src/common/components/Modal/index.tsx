import { ReactNode, RefObject, createContext, useCallback, useContext, useMemo, useRef } from "react"
import { CSSTransition } from "react-transition-group"
import { useImmer } from "use-immer"
import styles from './styles.module.scss'


function useMakeContext(rootElementRef?: RefObject<HTMLElement>) {
  const blockRef = useRef(null)
  const [layers, updateLayers] = useImmer<ReactNode[]>([])

  const addLayer = useCallback((layer: ReactNode) => {
    updateLayers(layers => {
      layers.push(layer)
    })
    return () => {
      updateLayers(layers => {
        layers.pop()
      })
    }
  }, [updateLayers])

  return useMemo(() => ({
    layers,
    addLayer,
    blockRef,
    rootElementRef,
  }), [addLayer, layers, rootElementRef])
}


const Context = createContext<ReturnType<typeof useMakeContext> | undefined>(undefined)


export function ModalProvider({
  children,
  rootElementRef,
}: {
  children: ReactNode
  rootElementRef?: RefObject<HTMLElement>
}) {
  const context = useMakeContext(rootElementRef)
  const nodeRef = context.blockRef

  return (
    <Context.Provider value={context}>
      {children}
      <CSSTransition
        in={context.layers.length > 0}
        timeout={{ enter: 100, exit: 200 }}
        nodeRef={nodeRef}
        mountOnEnter
        unmountOnExit
        classNames={{
          enter: styles.fadeEnter,
          enterActive: styles.fadeEnterActive,
          exit: styles.fadeExit,
          exitActive: styles.fadeExitActive,
        }}
      >
        <div ref={nodeRef} className={styles.block}>
          {context.layers[context.layers.length - 1]}
        </div>
      </CSSTransition>
    </Context.Provider>
  )
}


export function useModal() {
  const context = useContext(Context)
  if (context === undefined) {
    throw new Error(`use of useBlockUI outside the provider`)
  }
  const { addLayer, blockRef, rootElementRef } = context
  return { addLayer, blockRef, rootElementRef }
}


export function useBlockUI() {
  const { addLayer } = useModal()
  return useCallback(async (cb: () => Promise<unknown>) => {
    const unlock = addLayer(<progress />)
    try {
      await cb()
    }
    finally {
      unlock()
    }
  }, [addLayer])
}
