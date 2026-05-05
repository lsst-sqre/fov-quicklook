import { easing, SkyCoord } from '@stellar-globe/stellar-globe'
import StellarGlobe, { AppHandle } from '@stellar-globe/app'
import { FromApp, StateManager, ToApp } from '@stellar-globe/app/commTools'
import { useEffect, useRef } from 'react'


type OnStoreChange = NonNullable<Parameters<typeof StellarGlobe>[0]['onStoreChange']>


function useMakeContext(appRef: React.MutableRefObject<AppHandle>) {
  const ctx = useRef<{
    stateManager: StateManager<unknown>,
    ws: WebSocket,
  }>(null!)

  useEffect(() => {
    const initialState = appRef.current.getState()
    const originalHash = location.hash
    const commId = location.hash.slice(1)
    location.hash = ''
    const ws = new WebSocket(`ws://localhost:8000/comms/${commId}`)
    const stateManager = new StateManager(initialState)
    ctx.current = { stateManager, ws }
    const handleOpenMessage = (e: MessageEvent) => {
      const msg: ToApp['Open'] = JSON.parse(e.data)
      const ready: FromApp['Ready'] = {
        type: 'Ready',
        revision: stateManager.revision,
        state: initialState,
      }
      typedRespondToQuery('Ready', ws, msg.queryId, ready)
      ws.onmessage = handleMessage
    }
    ws.onmessage = handleOpenMessage
    const handleMessage = (e: MessageEvent) => {
      const msg = JSON.parse(e.data)
      const type: keyof ToApp = msg.type
      switch (type) {
        case 'Dispatch': {
          const { action } = msg as ToApp['Dispatch']
          appRef.current.dispatchAction(action)
          break
        }
        case 'JumpTo': {
          const { ra, dec, fov, duration, easingFunction } = msg as ToApp['JumpTo']
          const globe = appRef.current.globe()
          const coord = SkyCoord.fromRad(ra, dec)
          globe.camera.jumpTo({ fovy: fov }, { coord, duration: 1000 * duration, easingFunction: easingFunction && easing[easingFunction] })
          break
        }
        default:
          alert(`Unknown message type: ${type}`)
      }
    }
    return () => {
      ws.close()
      location.hash = originalHash
    }
  }, [appRef])

  const onStoreChange: OnStoreChange = e => {
    const { stateManager, ws } = ctx.current
    const patch = stateManager.pushState(e.state)
    const msg: FromApp['StoreChanged'] = {
      type: 'StoreChanged',
      ...patch,
    }
    ws.send(safeStringify(msg))
  }

  return {
    onStoreChange,
  }
}


function typedRespondToQuery<T extends keyof FromApp>(type: T, ws: WebSocket, queryId: string, data: Omit<FromApp[T], 'type'>) {
  const payload = { ...data, type }
  respondToQuery(ws, queryId, safeStringify(payload))
}


function respondToQuery(ws: WebSocket, queryId: string, content: string) {
  ws.send(safeStringify({
    type: 'queryResponse',
    queryId,
    content,
  }))
}

function safeStringify(obj: unknown) {
  return JSON.stringify(obj, (_key, value) => {
    if (value === undefined) {
      return null
    }
    return value
  })
}

function App() {
  const appRef = useRef<AppHandle>(null!)
  const { onStoreChange } = useMakeContext(appRef)

  return (
    <div
      style={{ height: '100vh' }}
    >
      <StellarGlobe
        ref={appRef}
        onStoreChange={onStoreChange}
        catchAllKeyboardEvents
      />
    </div>
  )
}


export default App
