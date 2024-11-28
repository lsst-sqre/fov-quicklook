import { GlobeHandle } from "@stellar-globe/react-stellar-globe"
import { angle, SkyCoord } from "@stellar-globe/stellar-globe"
import { createContext, FC, ReactNode, RefObject, useCallback, useContext, useMemo, useRef } from "react"
import { QuicklookHandle } from "../../../StellarGlobe/Quicklook/QuicklookLayer"
import { useQuicklookStatus } from "./quicklook"
import { DialogContext, DialogContextHandle } from "@stellar-globe/react-draggable-dialog"
// import { RubinTileHandle } from "./RubinTileLayer/RubinTileComponent"


type ContextType = {
  globeHandle: RefObject<GlobeHandle>,
  quicklookHandle: RefObject<QuicklookHandle>,
  currentQuicklook: ReturnType<typeof useQuicklookStatus>
  dialogContext: RefObject<DialogContextHandle>
}

// eslint-disable-next-line react-refresh/only-export-components
const Context = createContext<ContextType | undefined>(undefined)

type HomeContextProps = {
  children: ReactNode
}


// eslint-disable-next-line react-refresh/only-export-components
function HomeContextProvider({ children }: HomeContextProps) {
  const globeHandle = useRef<GlobeHandle>(null)
  const quicklookHandle = useRef<QuicklookHandle>(null)
  const currentQuicklook = useQuicklookStatus()
  const dialogContext = useRef<DialogContextHandle>(null)

  const defaultPositionHint = useMemo(() => ({
    right: 8,
    top: 8,
  }), [])

  const context: ContextType = {
    globeHandle,
    quicklookHandle,
    currentQuicklook,
    dialogContext,
  }

  return (
    <Context.Provider value={context}>
      <DialogContext ref={dialogContext} defaultPositionHint={defaultPositionHint} >
        {children}
      </DialogContext>
    </Context.Provider>
  )
}


export function wrapByHomeContext<P extends JSX.IntrinsicAttributes>(Component: FC<P>): FC<P> {
  const MyFunction = (props: P) => {
    return (
      <HomeContextProvider>
        <Component {...props} />
      </HomeContextProvider>
    )
  }
  return MyFunction
}


export function useHomeContext() {
  const context = useContext(Context)
  if (context === undefined) {
    throw new Error(`useHomeContext must be in HomeContextProvider`)
  }
  return context
}


export function useGlobe() {
  const { globeHandle } = useHomeContext()
  return globeHandle.current?.()
}


export function useResetView() {
  const { globeHandle } = useHomeContext()
  return useCallback((duration: number = 400) => {
    globeHandle.current?.().camera.jumpTo({ fovy: angle.deg2rad(3.6), roll: 0 }, { coord: SkyCoord.fromDeg(0, 0), duration })
  }, [globeHandle])
}


// export function useRubinTileLayer() {
//   const { tileLayerHandle } = useHomeContext()
//   return tileLayerHandle.current?.layerRef.current
// }
