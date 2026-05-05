import { useMemo } from "react"
import { Keybind } from "../../../common/components/keybindings"
import { useStateHistory } from "../../store/StateHistoryProvider"
import { appStateHistoryActions, useAppDispatch } from "../../store/hooks"


export function useHistoryKeybindings() {
  const history = useStateHistory()
  const dispatch = useAppDispatch()

  return useMemo(() => {
    const historyUndo: Keybind = {
      action() {
        if (history.currentIndex + 1 < history.records.length) {
          dispatch(appStateHistoryActions.timeTravel({ index: history.currentIndex + 1 }))
        }
        else {
          return { preventDefault: false }
        }
      },
      shortcut: 'Meta+Z',
    }

    const historyRedo: Keybind = {
      action() {
        if (history.currentIndex >= 1) {
          dispatch(appStateHistoryActions.timeTravel({ index: history.currentIndex - 1 }))
        }
        else {
          return { preventDefault: false }
        }
      },
      shortcut: 'Meta+Shift+Z',
    }

    return {
      historyUndo,
      historyRedo,
    }
  }, [dispatch, history])
}
