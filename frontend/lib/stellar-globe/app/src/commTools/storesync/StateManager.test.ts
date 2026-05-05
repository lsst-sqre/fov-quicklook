import { StateManager } from './StateManager'

describe('StateManager', () => {
  let stateManager: StateManager<any>

  beforeEach(() => {
    stateManager = new StateManager({ count: 0 }, 3)
  })

  test('should initialize with the initial state', () => {
    expect(stateManager.currentState()).toEqual({ count: 0 })
  })

  test('should push a new state and return the patch', () => {
    const newState = { count: 1 }
    const patch = stateManager.pushState(newState)

    expect(patch.baseRevision).toBe(0)
    expect(patch.patch).toEqual([{ op: 'replace', path: '/count', value: 1 }])
  })

  test('should return the current state', () => {
    const newState = { count: 1 }
    stateManager.pushState(newState)

    expect(stateManager.currentState()).toEqual(newState)
  })

  test('should generate a patch from a base revision', () => {
    const newState = { count: 1 }
    stateManager.pushState(newState)

    const patch = stateManager.patchFrom(0)

    expect(patch.newRevision).toBe(1)
    expect(patch.patch?.patch).toEqual([{ op: 'replace', path: '/count', value: 1 }])
    expect(patch.patch?.baseRevision).toBe(0)
  })

  test('should return the current state if base revision is invalid', () => {
    const newState = { count: 1 }
    stateManager.pushState(newState)

    const patch = stateManager.patchFrom(2)

    expect(patch.newRevision).toBe(1)
    expect(patch.state).toEqual(newState)
  })

  test('should return the current revision', () => {
    expect(stateManager.revision).toBe(0)

    const newState = { count: 1 }
    stateManager.pushState(newState)

    expect(stateManager.revision).toBe(1)
  })
})