import { generateJsonPatch } from ".."
import { BatchPatch, Patch, StateManager as StateManagerType } from "../../../types/commTools/StateManager"
import { SizeLimitedMap } from "./SizeLimitedMap"


export class StateManager<S> {
  private _revision = 0
  private history: SizeLimitedMap<number, S>

  constructor(
    initialState: S,
    maxHistoryLength = 5,
  ) {
    this.history = new SizeLimitedMap(maxHistoryLength)
    this.history.set(this._revision, initialState)
  }

  currentState(): S {
    return this.history.get(this._revision)!
  }

  pushState(state: S): Patch {
    const baseState = this.currentState()
    this._revision++
    this.history.set(this._revision, state)
    return {
      baseRevision: this._revision - 1,
      patch: generateJsonPatch(baseState, state),
    }
  }

  patchFrom(baseRevision: number): BatchPatch<S> {
    const original = this.history.get(baseRevision)
    if (original === undefined) {
      return {
        newRevision: this._revision,
        state: this.currentState()
      }
    }
    return {
      newRevision: this._revision,
      patch: {
        baseRevision,
        patch: generateJsonPatch(original, this.currentState()),
      },
    }
  }

  get revision() {
    return this._revision
  }

  clear() {
    this._revision = 0
    this.history.clear()
  }
}


type AssertTypeImplements<T, U extends T> = T
type _TypeCheck1 = AssertTypeImplements<typeof StateManagerType, typeof StateManager>

