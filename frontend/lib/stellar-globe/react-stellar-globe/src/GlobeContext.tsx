import { CameraMode, Globe, Layer } from '@stellar-globe/stellar-globe'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import { useInstanceVariable } from './hooks/useInstanceVariable'


type LayerKey = unknown


function useLayerKey() {
  const keyRef = useRef({})
  return keyRef.current
}


type GlobeState = {
  globe: Globe | undefined
  layerFactories: Map<LayerKey, { factory: (globe: Globe) => Layer, el: HTMLDivElement, visible: boolean }>
  layers: Map<LayerKey, { layer: Layer, el: HTMLDivElement }>
}


type CameraParams = {
  theta: number
  phi: number
  za: number
  zd: number
  zp: number
  fovy: number
  roll: number
}

type NativeGlobeOptions = Required<NonNullable<ConstructorParameters<typeof Globe>[1]>>

export type GlobeOptions = {
  jsdomTest?: boolean
  preserveBuffer?: NativeGlobeOptions["preserveBuffer"]
  noDefaultLayers?: NativeGlobeOptions["noDefaultLayers"]
  projection?: CameraMode
  retina?: boolean
  cameraParams?: CameraParams
}

export type GlobeHooks = {
  onInit?: (globe: Globe) => void
  onRelease?: (globe: Globe) => void
}


export function useGenerateContext({
  jsdomTest,
  projection = 'STEREOGRAPHIC',
  retina = false,
  preserveBuffer,
  noDefaultLayers,
  cameraParams,
  onInit,
  onRelease,
}: GlobeOptions & GlobeHooks) {
  const containerRef = useRef<HTMLDivElement>(null)
  const state = useInstanceVariable<GlobeState>(() => ({
    globe: undefined,
    layers: new Map(),
    layerFactories: new Map(),
  }))
  const initialProps = useRef({
    retina,
    noDefaultLayers,
    cameraParams,
    projection,
  })
  const { layers, layerFactories } = state

  const registerLayer = useCallback((key: LayerKey, el: HTMLDivElement, visible: boolean, factory: (globe: Globe) => Layer) => {
    // GlobeとLayerが同時にmountされる場合は
    // Globe.render, Layer.renader, Layer.useEffect, Globe.useEffect の順に実行される
    // useLayerBindで設定されたuseEffectが実行されるタイミングではglobeはまだ初期化されていない
    if (state.globe) {
      const layer = factory(state.globe)
      layers.set(key, { layer, el })
      if (visible) {
        state.globe.addLayer(layer)
      }
    }
    else {
      layerFactories.set(key, { factory, el, visible })
    }
  }, [layerFactories, layers, state])

  const domBasedSortFunc = useCallback((a: Layer, b: Layer) => {
    const inverse = new Map<Layer, HTMLDivElement>()
    for (const [, { el, layer }] of layers) {
      inverse.set(layer, el)
    }
    return compareDomPosition(inverse.get(a), inverse.get(b))
  }, [layers])

  // 初回に実行して欲しくないeffectはinitGlobeの前に書く

  useEffect(function toggleProjection() {
    if (state.globe) {
      state.globe.camera.jumpTo({ mode: projection })
    }
  }, [projection, state])

  useEffect(function toggleRetina() {
    if (state.globe) {
      state.globe.camera.setRetina(retina)
    }
  }, [retina, state])

  useEffect(function updateCamera() {
    if (state.globe) {
      if (cameraParams) {
        Object.assign(state.globe.camera, extractCameraParams(cameraParams))
        state.globe.requestRefresh()
      }
    }
  }, [cameraParams, state.globe])

  useEffect(function initGlobe() {
    const globe = new Globe(containerRef.current!, {
      jsdomTest,
      preserveBuffer,
      viewOptions: {
        ...initialProps.current.cameraParams,
        retina: initialProps.current.retina,
        mode: initialProps.current.projection,
      },
      noDefaultLayers: initialProps.current.noDefaultLayers,
    })
    onInit?.(globe)
    globe.layerSorter.setSortFunc(domBasedSortFunc)
    state.globe = globe
    for (const [key, { factory, el, visible }] of layerFactories) {
      registerLayer(key, el, visible, factory)
    }
    layerFactories.clear()
    return () => {
      for (const [, { layer }] of Array.from(layers).reverse()) {
        layer.release()
      }
      layers.clear()
      onRelease?.(globe)
      globe.release()
      if (layerFactories.size > 0) {
        console.error(layerFactories)
        throw new Error(`layerFactories is not empty`)
      }
      state.globe = undefined
    }
  }, [domBasedSortFunc, jsdomTest, layerFactories, layers, onInit, onRelease, preserveBuffer, registerLayer, state])

  return useMemo(() => ({
    state,
    containerRef,
    registerLayer,
  }), [registerLayer, state])
}


export const GlobeContext = createContext<ReturnType<typeof useGenerateContext> | undefined>(undefined)


function useGlobeContext() {
  const context = useContext(GlobeContext)
  if (context === undefined) {
    throw new Error(`use of useGlobeContext outside <$Globe />`)
  }
  return context
}


export function useGetGlobe() {
  const context = useGlobeContext()
  return useCallback(() => {
    if (context.state.globe === undefined) {
      throw new Error(`globe has not been set up yet`)
    }
    return context.state.globe
  }, [context])
}


export function useLayerBind<L extends Layer>(factory: (globe: Globe) => Layer, visible: boolean) {
  const key = useLayerKey()
  const { state, registerLayer } = useGlobeContext()
  const { layerFactories, layers } = state
  const el = useRef<HTMLDivElement>(null)

  useEffect(function toggleVisible() {
    // これはregisterThisLayerより先に登録する必要がある。
    // そうしないと二重にaddLayerされてしまう。
    const ready = layers.get(key)
    if (ready) {
      const { layer } = ready
      if (visible) {
        layer.globe.addLayer(layer)
      }
      else {
        layer.globe.removeLayer(layer)
      }
    }
  }, [key, layers, visible])

  useEffect(
    function registerThisLayer() {
      registerLayer(key, el.current!, visible, factory)
      return () => {
        layerFactories.delete(key)
        if (layers.has(key)) {
          // Globe$とLayer$が同時にunmountされる場合、Globe$が先にunmountされる。
          // その時はGlobe$のunmountに先立って、initGlobeのcleanup内でreleaseされる。
          layers.get(key)!.layer.release()
          layers.delete(key)
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      factory,
      key,
      layerFactories,
      layers,
      registerLayer,
    ],
  )

  const ifLayerReady = useCallback((cb: (layer: L) => void | (() => void)) => {
    const ready = layers.get(key)
    if (ready) {
      const { layer } = ready
      return cb(layer as L)
    }
  }, [key, layers])

  return {
    node: <div ref={el} />,
    ifLayerReady,
  }
}


type PickKeysOf<M, T> = {
  [K in keyof M]: M[K] extends T ? K : never
}[keyof M]


export function makePureLayerComponent<
  Props extends object = object,
  VisibleKey extends PickKeysOf<Props, boolean | undefined> = PickKeysOf<Props, boolean | undefined>,
  L extends Layer = Layer,
>(
  factory: (globe: Globe, props: Props) => L,
  visibleKey: VisibleKey,
) {
  return (props: Props) => {
    const { [visibleKey]: visible = true, ...rest } = props
    const memoizedFactory = useCallback(
      (globe: Globe) => factory(globe, props),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [...Object.keys(rest), ...Object.values(rest)],
    )
    const { node } = useLayerBind(memoizedFactory, visible as boolean)
    return node
  }
}


export function mountOndemand<
  Props extends object = object,
  VisibleKey extends PickKeysOf<Props, boolean | undefined> = PickKeysOf<Props, boolean | undefined>,
>(
  Component: React.ComponentType<Props>,
  visibleKey: VisibleKey,
) {
  return function WrappedComponent(props: Props) {
    const { [visibleKey]: visible = true } = props
    const [initialized, setInitialized] = useState(visible)
    useEffect(() => {
      if (visible) {
        setInitialized(true)
      }
    }, [visible])
    return initialized && <Component {...props} />
  }
}


export function setDisplayName(components: { [name: string]: { displayName?: string } | React.FC<never> }) {
  for (const k of Object.keys(components)) {
    components[k].displayName = k
  }
}


function compareDomPosition(aDom?: HTMLDivElement, bDom?: HTMLDivElement) {
  if (aDom && bDom) {
    const mask = aDom.compareDocumentPosition(bDom)
    return (mask & 2) !== 0 ? +1 : (
      (mask & 4) !== 0 ? -1 : 0
    )
  }
  const reactLayerFirst = +1 // +1: true, -1: false
  if (aDom) {
    return reactLayerFirst
  }
  if (bDom) {
    return -reactLayerFirst
  }
  return 0
}


function extractCameraParams(camera: CameraParams): CameraParams {
  const { theta, phi, za, zd, zp, fovy, roll } = camera
  return { theta, phi, za, zd, zp, fovy, roll }
}
