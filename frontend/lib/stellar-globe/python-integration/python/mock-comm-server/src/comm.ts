import { makeStore } from '@stellar-globe/app'
import { FromApp, StateManager, ToApp, validateAction, validateToAppMessage } from '@stellar-globe/app/commTools'


export class BadRequestError extends Error {
  constructor(message: string, readonly status = 400) {
    super(message)
  }
}


type Store = ReturnType<typeof makeStore>
type State = ReturnType<Store['getState']>


export class Comm {
  private queryResponses: Map<string, any> = new Map()
  readonly id: string
  private store: ReturnType<typeof makeStore>
  private stateManager: StateManager<State>
  private messages: any[] = []

  constructor(openMessage: ToApp['Open']) {
    this.id = openMessage.id
    this.store = makeStore({ storageKey: 'reference-comm' })
    this.stateManager = new StateManager<State>(this.store.getState(), 2)
    this.respondToQuery<'Ready'>(openMessage.queryId, {
      type: 'Ready',
      revision: this.stateManager.revision,
      state: this.store.getState(),
    })
  }

  private respondToQuery<K extends keyof FromApp>(queryId: string, response: FromApp[K]) {
    this.queryResponses.set(queryId, response)
  }

  onReceiveMessage(msg: any) {
    if (isDispatchMessage(msg)) {
      if (!validateAction(msg.action)) {
        throw new BadRequestError(`Invalid action: ${JSON.stringify(msg.action)}`)
      }
      this.store.dispatchAction(msg.action)
      const patch = this.stateManager.pushState(this.store.getState())
      this.sendToClient({
        type: 'StoreChanged',
        ...patch,
      })
      return
    }
    if (isQueryStateMessage(msg)) {
      const batchPatch = this.stateManager.patchFrom(msg.baseRevision)
      this.respondToQuery(msg.queryId, {
        type: 'QueryStateResponse',
        ...batchPatch,
      })
      return
    }
    if (isCloseMessage(msg)) {
      this.sendToClient({ type: 'Closed' })
      return
    }
    if (isQuerySnapshot(msg)) {
      this.queryResponses.set(msg.queryId, sampleImageUrl())
      return
    }
    if (
      isUpdateWidgetState(msg)
      ||
      isLockFrame(msg)
      ||
      isUnlockFrame(msg)
      ||
      isJumpTo(msg)
    ) {
      return
    }
    throw new BadRequestError(`Invalid message: ${JSON.stringify(msg)}`)
  }

  getQueryResponse(queryId: string) {
    const response = this.queryResponses.get(queryId)
    this.queryResponses.delete(queryId)
    return response
  }

  private sendToClient(msg: FromApp[keyof FromApp]) {
    this.messages.push(msg)
  }

  getFirstMessage() {
    return this.messages.shift()
  }
}


function createIs<T extends keyof ToApp>(type: T) {
  const f = Object.assign((msg: any): msg is ToApp[T] => {
    const { errors } = validateToAppMessage(type, msg)
    f.errors = errors
    return errors.length === 0
  }, {
    errors: [] as string[],
  })
  return f
}

const isDispatchMessage = createIs('Dispatch')
const isQueryStateMessage = createIs('QueryState')
const isCloseMessage = createIs('Close')
const isUpdateWidgetState = createIs('UpdateWidgetState')
const isQuerySnapshot = createIs('QuerySnapshot')
const isLockFrame = createIs('LockFrame')
const isUnlockFrame = createIs('UnlockFrame')
const isJumpTo = createIs('JumpTo')


function sampleImageUrl() {
  // data url of a 1x1 green png
  return `data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg+M/wHwAEAQH/cetH5QAAAABJRU5ErkJggg==`
}
