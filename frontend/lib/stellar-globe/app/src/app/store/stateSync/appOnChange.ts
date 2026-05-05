import { AppStore, AppState } from ".."

export function appOnChange<T>(store: AppStore, select: (state: AppState) => T, onChange: (newValue: T, prevValue: T) => void) {
  let prevValue = select(store.getState())

  const onStoreChange = () => {
    const newValue = select(store.getState())
    if (!Object.is(prevValue, newValue)) {
      try {
        onChange(newValue, prevValue)
      } finally {
        prevValue = newValue
      }
    }
  }

  return store.subscribe(onStoreChange)
}
