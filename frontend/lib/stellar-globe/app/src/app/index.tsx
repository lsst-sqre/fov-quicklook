import '@stellar-globe/react-draggable-dialog/style.css'
import { Globe } from '@stellar-globe/stellar-globe'
import '@szhsin/react-menu/dist/index.css'
import classNames from 'classnames'
import 'material-symbols/outlined.css'
import { CSSProperties, forwardRef, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Provider } from "react-redux"
import { MenuProvider } from '../common/components/Menu/MenuContext'
import { ModalProvider } from '../common/components/Modal'
import { useIsFullscreen } from '../common/hooks/useFullscreen'
import MainMenu from "./MainMenu"
import { MainViewer } from "./MainViewer"
import { AppContextProvider, useMakeContext, useSetupAppHandle } from "./context"
import { AppDragAndDrop } from './AppDragAndDrop'
import { Dialogs } from './features/dialogs/Dialogs'
import { KeybindsProvider } from './keybindings/appKeybindings'
import { AppState, StoreChangeEvent } from './store'
import { StateHistoryProvider } from './store/StateHistoryProvider'
import { AppStateWithComputed } from './store/computedState'
import { useLocalStorageSync } from './store/stateSync/StorageSync'
import { useHashSync } from './store/stateSync/hashSync'
import styles from './style.module.scss'
import { Indicator } from './features/indicator/Indicator'


export type AppProps = {
  hashSync?: boolean
  storageSync?: boolean
  storageKey?: string
  catchAllKeyboardEvents?: boolean
  floatingLayerElement?: HTMLElement
  floatingLayerZIndex?: CSSProperties['zIndex']
  activeOnInit?: boolean
  onStoreChange?: (e: StoreChangeEvent) => void
  initialState?: AppState
}

export type AppHandle = {
  globe: () => Globe
  dispatchAction: (action: { type: string, payload: unknown }) => void
  getState: () => AppStateWithComputed,
  activate: () => void
  deactivate: () => void
}


export const App = forwardRef<AppHandle, AppProps>(({
  hashSync = false,
  storageSync = false,
  catchAllKeyboardEvents = true,
  floatingLayerElement, // Dialogs, Menuはここに作られる
  floatingLayerZIndex,
  activeOnInit = true,
  storageKey = '@stellar-globe/app/store-settings',
  onStoreChange,
  initialState,
}, ref) => {
  const context = useMakeContext({ active: activeOnInit, storageKey, onStoreChange, initialState, hashSync })
  useSetupAppHandle(ref, context)
  const { rootElementRef, store, stateHistory } = context
  const { isFullscreen } = useIsFullscreen()
  const { element: menuLayerElement, ref: menuLayer } = useElement<HTMLDivElement>([isFullscreen])
  const { element: dialogLayerElement, ref: dialogLayer } = useElement<HTMLDivElement>([isFullscreen])

  useHashSync({ store, enabled: hashSync })
  useLocalStorageSync({ store, enabled: storageSync, storageKey: store.getState().initializerParams.storageKey })

  return (
    <AppContextProvider context={context} >
      <Provider store={store}>
        <div
          className={classNames(styles.main, styles.theme)}
          ref={rootElementRef}
          tabIndex={catchAllKeyboardEvents ? undefined : -1}
        >
          <MenuProvider portal={menuLayerElement}>
            <Dialogs portal={dialogLayerElement} />
            <StateHistoryProvider stateHistory={stateHistory}>
              <ModalProvider rootElementRef={rootElementRef}>
                <KeybindsProvider containerRef={rootElementRef} catchAllEvents={catchAllKeyboardEvents}>
                  <AppDragAndDrop>
                    <MainViewer />
                    <MainMenu />
                  </AppDragAndDrop>
                  <Indicator />
                </KeybindsProvider>
              </ModalProvider>
            </StateHistoryProvider>
          </MenuProvider>
        </div>
        {createPortal((
          <div className={classNames(styles.theme, styles.floatingLayer)} style={{ zIndex: floatingLayerZIndex }} >
            <div ref={dialogLayer} />
            <div data-no-dnd ref={menuLayer} />
          </div>
        ), isFullscreen && rootElementRef.current || (floatingLayerElement ?? document.body))}
      </Provider >
    </AppContextProvider>
  )
})


function useElement<T extends HTMLElement>(deps: unknown[]) {
  const ref = useRef<T>(null)
  const [element, setElement] = useState<T>()
  useEffect(
    () => {
      setElement(ref.current ?? undefined)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    deps,
  )
  return { element, ref }
}
