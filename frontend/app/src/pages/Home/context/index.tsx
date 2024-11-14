import { GlobeHandle } from "@stellar-globe/react-stellar-globe"
import { FC, ReactNode, RefObject, createContext, useContext, useRef } from "react"
import { useQuicklookStatus } from "./quicklook"
import { QuicklookHandle } from "../../../StellarGlobe/Quicklook/QuicklookLayer"
// import { RubinTileHandle } from "./RubinTileLayer/RubinTileComponent"


type ContextType = {
  globeHandle: RefObject<GlobeHandle>,
  quicklookHandle: RefObject<QuicklookHandle>,
  currentQuicklook: ReturnType<typeof useQuicklookStatus>
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

  const context: ContextType = {
    globeHandle,
    quicklookHandle,
    currentQuicklook,
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


// export function useRubinTileLayer() {
//   const { tileLayerHandle } = useHomeContext()
//   return tileLayerHandle.current?.layerRef.current
// }
