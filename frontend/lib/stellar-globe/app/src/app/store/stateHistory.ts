import { Action, ActionCreatorWithPayload, Dispatch, Middleware, MiddlewareAPI, createAction } from '@reduxjs/toolkit'
import { Debounce } from '../../common/utils/debounce'


const setStateKey = 'history/set_state'
const timeTravel = createAction<{ index: number }>('history/time_travel')
const setState = createAction<any>(setStateKey)


export function makeStateHistoryActions<S>(): {
  setState: ActionCreatorWithPayload<S, 'history/set_state'>,
  timeTravel: ActionCreatorWithPayload<{ index: number }, 'history/time_travel'>,
} {
  return {
    setState,
    timeTravel,
  } as any
}


type Options = {
  maxHistory?: number
}


// eslint-disable-next-line @typescript-eslint/ban-types
type HistoryChagneEvent = {}


export type StateHistoryRecord = {
  state: unknown
  summary?: string
  type: string
  id: number
}


let seq = 0


export const makeStateHistory = ({ maxHistory = 20 }: Options = {}) => {
  const records: StateHistoryRecord[] = []
  let currentIndex = 0
  const changeCallbacks: ((e: HistoryChagneEvent) => void)[] = []
  const debounce = Debounce(200)

  const middleware = (({ getState }: MiddlewareAPI<Dispatch<Action>, unknown>) => (next: Dispatch<Action>) => (action: Action) => {
    if (timeTravel.match(action)) {
      const { index } = action.payload
      if (0 <= index && index < records.length) {
        currentIndex = index
        const { state } = records[index]
        changeCallbacks.forEach(cb => cb({}))
        return next(setState(state))
      }
    }

    if (records.length === 0) {
      records.unshift({ state: getState(), summary: 'Page Loaded', type: action.type, id: ++seq })
    }

    const nextAction = next(action)

    if (shouldTrack(action)) {
      debounce(() => {
        records.splice(0, currentIndex)
        currentIndex = 0
        const summary = debounce.skippedCalls() > 1 ? `Batch updates` : action.meta[trackKey].summary
        records.unshift({ state: getState(), summary, type: action.type, id: ++seq })
        while (records.length > maxHistory) {
          records.pop()
        }
        changeCallbacks.forEach(cb => cb({}))
      })
    }

    return nextAction
  }) as Middleware

  return {
    middleware,
    records,
    currentIndex: () => currentIndex,
    onChange: (cb: (e: HistoryChagneEvent) => void) => {
      changeCallbacks.push(cb)
      return () => {
        const i = changeCallbacks.indexOf(cb)
        if (i >= 0) {
          changeCallbacks.splice(i, 1)
        }
      }
    },
  }
}


const trackKey = Symbol('history/track')


type TrackMeta = {
  summary?: string
}


export function trackAction<T>(action: T, summary?: string): T {
  const trackMeta: TrackMeta = {
    summary,
  }
  // @ts-ignore
  action.meta = action.meta ?? {}
  // @ts-ignore
  action.meta[trackKey] = trackMeta
  return action
}


function shouldTrack<A extends Action>(action: A): action is A & { meta: { [trackKey]: TrackMeta } } {
  // @ts-ignore
  return !!action.meta?.[trackKey]
}
