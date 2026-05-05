import { ReactNode, RefObject, createContext, useContext, useEffect, useMemo, useRef, useState } from "react"


function useMakeContext({ portal }: { portal: HTMLElement | undefined }) {
  return useMemo(() => ({
    container: portal,
  }), [portal])
}


const Context = createContext<ReturnType<typeof useMakeContext> | undefined>(undefined)


type ProviderProps = {
  children: ReactNode
  portal?: HTMLElement
}


export function MenuProvider({ children, portal }: ProviderProps) {
  const context = useMakeContext({ portal })
  return <Context.Provider value={context}>{children}</Context.Provider>
}


export function useMenuContainer() {
  const context = useContext(Context)
  return context?.container
}
