import { ReactNode, RefObject, createContext, useContext, useEffect, useMemo, useRef } from "react"
import { generateShortcutFromEvent, normalizeShortcut } from "../utils/keybindingsUtils"


function useMakeContext({
  containerRef,
  keybinds,
  catchEventsOutsideContainer,
}: {
  containerRef: RefObject<HTMLElement>
  keybinds: { [shortcut: string]: Keybind }
  catchEventsOutsideContainer: boolean,
}) {
  const shortcutMap = useMemo(() => {
    return new Map(Object.entries(keybinds).map(([_, kb]) => [normalizeShortcut(kb.shortcut), kb]))
  }, [keybinds])

  const activeKeybind = useRef<{ shortcut: string, stop: () => void } | undefined>(undefined)

  useEffect(function setupKeybindsEventListeners() {
    const keydown = (e: KeyboardEvent) => {
      if (
        e.target instanceof Node &&
        !['INPUT', 'TEXTAREA'].includes(e.target.nodeName) && (
          catchEventsOutsideContainer ||
          containerRef.current?.contains(e.target)
        )
      ) {
        const shortcut = generateShortcutFromEvent(e)

        if (activeKeybind.current && activeKeybind.current.shortcut !== shortcut) {
          activeKeybind.current.stop()
        }

        const kb = shortcutMap.get(shortcut)
        if (kb) {
          if (kb.press && activeKeybind.current?.shortcut !== shortcut) {
            const stop = kb.press()
            activeKeybind.current = {
              shortcut,
              stop,
            }
          }
          const actionResult = kb.action?.()
          const { preventDefault } =
            (actionResult instanceof Promise ? undefined : actionResult) ?? { preventDefault: true }
          if (preventDefault) {
            e.preventDefault()
          }
        }
      }
    }
    document.addEventListener('keydown', keydown)

    const keyup = (e: KeyboardEvent) => {
      if (activeKeybind.current) {
        activeKeybind.current.stop()
        activeKeybind.current = undefined
      }
    }
    document.addEventListener('keyup', keyup)

    return () => {
      document.removeEventListener('keyup', keyup)
      document.removeEventListener('keydown', keydown)
    }
  }, [catchEventsOutsideContainer, containerRef, keybinds, shortcutMap])

  return useMemo(() => ({
    keybinds,
  }), [keybinds])
}
const Context = createContext<ReturnType<typeof useMakeContext> | undefined>(undefined)

type ActionResult = void | Promise<void> | { preventDefault?: boolean }


export type Keybind = {
  shortcut: string
  action?: () => ActionResult
  press?: () => () => void
}


export function makeKeybindsEnvironment<T extends Record<string, Keybind>>(
  useKeybinds: () => T,
) {
  type ProviderProps = {
    children?: ReactNode
    containerRef: RefObject<HTMLElement>
    catchAllEvents?: boolean
  }

  const KeybindsProvider = ({
    children, containerRef,
    catchAllEvents = false,
  }: ProviderProps) => {
    const keybinds = useKeybinds()
    const context = useMakeContext({ containerRef, keybinds, catchEventsOutsideContainer: catchAllEvents })
    return (
      <Context.Provider value={context}>
        {children}
      </Context.Provider>
    )
  }

  const useKeybind = (which?: keyof T) => {
    const context = useContext(Context)
    if (context === undefined) {
      throw new Error(`use of useKeybinds outside its provider`)
    }
    return which && (context.keybinds as T)[which]
  }

  const useKeybindShortcut = (which?: keyof T) => {
    return useKeybind(which)?.shortcut
  }

  const useKeybindAction = (which?: keyof T) => {
    return useKeybind(which)?.action
  }

  return { KeybindsProvider, useKeybindShortcut, useKeybindAction }
}
