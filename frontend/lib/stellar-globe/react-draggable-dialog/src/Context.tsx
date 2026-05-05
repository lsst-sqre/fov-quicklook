import { ReactNode, createContext, forwardRef, useCallback, useContext, useImperativeHandle, useMemo, useState } from "react"
import { useInstanceVariable } from "./hooks"
import { defaultPositionFinder } from "./positionFinder/defaultPositionFinder"
import { setDisplayName } from "./setDisplayName"
import { CSSPosition, Origin, Position, Rect, Size, TopLeft } from "./types"


export type DialogState = {
  rect: Rect
}


type ContextType = {
  portal?: HTMLElement
  dialogs: Map<number, DialogState>
  nextPosition: (size: Size, options: { positionHint?: TopLeft, origin: Origin }) => Position
  zIndex: Map<number, number>
  defaultPositionHint: CSSPosition | undefined
  raiseDialog: (id: number) => void
  rearrangeTrigger: unknown
}


const Context = createContext<ContextType | undefined>(undefined)


type Props = {
  children: ReactNode
  portal?: HTMLElement
  defaultPositionHint?: CSSPosition
  positionFinder?: (rects: Rect[], size: Size, options: { positionHint?: Position }) => Position
}


export type DialogContextHandle = {
  rearrange: () => void
}


// eslint-disable-next-line react/display-name
export const DialogContext = forwardRef<DialogContextHandle, Props>(({
  children,
  portal,
  positionFinder = defaultPositionFinder,
  defaultPositionHint,
}, ref) => {
  const dialogs = useInstanceVariable(() => new Map<number, DialogState>())
  const [zIndex, setZIndex] = useState(new Map<number, number>())
  const [rearrangeTrigger, rearrange] = useState({})

  useImperativeHandle(ref, () => ({
    rearrange: () => {
      dialogs.clear()
      rearrange({})
    },
  }), [dialogs])

  const raiseDialog = useCallback((id0: number) => {
    const z0 = zIndex.get(id0)!
    setZIndex(zIndex => {
      return new Map(
        [...zIndex.entries()]
          .sort((a, b) => a[1] - b[1])
          .map(([id, z], i) => [id, z === z0 ? zIndex.size - 1 : z > z0 ? i - 1 : i])
      )
    })
  }, [zIndex])

  const context: ContextType = useMemo(() => ({
    dialogs,
    portal,
    nextPosition: (size: Size, options: { positionHint?: TopLeft, origin: Origin }) => positionFinder(
      [...dialogs.values()].map(d => d.rect),
      size,
      {
        positionHint: options.positionHint,
        origin: options.origin,
      },
    ),
    zIndex,
    raiseDialog,
    defaultPositionHint,
    rearrangeTrigger,
  }), [defaultPositionHint, dialogs, portal, positionFinder, raiseDialog, rearrangeTrigger, zIndex])

  return (
    <Context.Provider value={context}>
      {children}
    </Context.Provider>
  )
})
setDisplayName({ DialogContext })


export function useDialogContext() {
  const context = useContext(Context)
  if (context === undefined) {
    throw new Error(`Use of useDialogContext outside its provider`)
  }
  return context
}
