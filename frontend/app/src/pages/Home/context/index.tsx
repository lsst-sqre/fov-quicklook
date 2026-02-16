import { GlobeHandle } from "@stellar-globe/react-stellar-globe"
import { angle, SkyCoord } from "@stellar-globe/stellar-globe"
import { createContext, FC, ReactNode, RefObject, useCallback, useContext, useRef } from "react"
import { QuicklookLayerHandle } from "../../../StellarGlobe/Quicklook/QuicklookLayer"
import { useQuicklookMetadata } from "./quicklook"


type ContextType = {
  globeHandle: RefObject<GlobeHandle>,
  quicklookLayerHandle: RefObject<QuicklookLayerHandle>,
  currentQuicklook: ReturnType<typeof useQuicklookMetadata>
}

// eslint-disable-next-line react-refresh/only-export-components
const Context = createContext<ContextType | undefined>(undefined)

type HomeContextProps = {
  children: ReactNode
}


// eslint-disable-next-line react-refresh/only-export-components
function HomeContextProvider({ children }: HomeContextProps) {
  const globeHandle = useRef<GlobeHandle>(null)
  const currentQuicklook = useQuicklookMetadata()
  const quicklookLayerHandle = useRef<QuicklookLayerHandle>(null)

  const context: ContextType = {
    globeHandle,
    currentQuicklook,
    quicklookLayerHandle,
  }

  return (
    <Context.Provider value={context}>
      {children}
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
