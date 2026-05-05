export class StateManager<S> {
  constructor(
    initialState: S,
    maxHistoryLength?: number
  )

  currentState(): S

  pushState(state: S): Patch
  patchFrom(baseRevision: number): BatchPatch<S>

  get revision(): number

  clear(): void
}


type Patch = {
  /** @TJS-type integer */
  baseRevision: number
  patch: unknown[]
}


type BatchPatch<S> = {
  /** @TJS-type integer */
  newRevision: number
  patch?: Patch
  state?: S
}