import { useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { AppState, AppStore } from "../store"
import { debounce } from "../utils/debounce"
import { deserialize, serialize } from "../utils/serialize"

/*

  このモジュールではURLのハッシュ部分のsearchParamsの_に情報を格納する機能を提供する。
  http://localhost:3000/#/home?_=... の...の部分に任意の情報をエンコードする。
  エンコードは与えられたデータをgzip圧縮し、base64エンコードしてURLセーフにするものである。
 */


type HashState = {
  cameraParams: AppState['home']['cameraParams']
  filterParams: AppState['home']['filterParams']
}


function hashState(state: AppState): HashState {
  return {
    cameraParams: state.home.cameraParams,
    filterParams: state.home.filterParams,
  }
}

export function useHashSync({
  store,
  enabled,
}: {
  store: AppStore
  enabled: boolean
}) {
  const [, setSearchParams] = useSearchParams()

  useEffect(() => {
    if (enabled) {
      const sync = debounce(200, () => {
        const serialized = serialize(hashState(store.getState()))
        setSearchParams({ _: serialized }, { replace: true })
      })
      const cleanup: (() => void)[] = [
        appOnChange(store, state => state.home.cameraParams, sync),
        appOnChange(store, state => state.home.filterParams, sync),
      ]
      return () => {
        while (cleanup.length > 0) {
          cleanup.pop()!()
        }
      }
    }
  }, [enabled, setSearchParams, store])
}

export const initialSearchParams = ((): Partial<HashState> => {
  const hash = window.location.hash
  if (!hash) return {}

  const hashParts = hash.slice(1).split('?')
  if (hashParts.length < 2) return {}

  const searchParams = new URLSearchParams(hashParts[1])
  const serialized = searchParams.get('_')

  if (!serialized) return {}

  try {
    return deserialize(serialized) as Partial<HashState>
  } catch (e) {
    console.error('Failed to deserialize hash state:', e)
    return {}
  }
})()

function appOnChange<T>(store: AppStore, select: (state: AppState) => T, onChange: (newValue: T, prevValue: T) => void) {
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
