import { useMemo } from "react"
import { makeKeybindsEnvironment } from "../../common/components/keybindings"
import { useDevelKeybindings } from "../features/devel/develKeybindings"
import { useToolsKeybindings } from "../features/regions/toolsKeybindings"
import { useViewKeybindings } from "../features/view/viewKeybindings"
import { useHistoryKeybindings } from "../features/history/historyKeybindings"
import { useSesameKeybindings } from "../features/sesame/SesameKeybindings"
import { useDialogsKeybindings } from "../features/dialogs/dialogsKeybindings"


export function useAppKeybinds() {
  const viewKeyBindings = useViewKeybindings()
  const develKeybindings = useDevelKeybindings()
  const toolsKeybindings = useToolsKeybindings()
  const historyKeybindings = useHistoryKeybindings()
  const sesameKeybindings = useSesameKeybindings()
  const dialogsKeybindings = useDialogsKeybindings()

  return useMemo(() => ({
    ...viewKeyBindings,
    ...develKeybindings,
    ...toolsKeybindings,
    ...historyKeybindings,
    ...sesameKeybindings,
    ...dialogsKeybindings,
  }), [develKeybindings, dialogsKeybindings, historyKeybindings, sesameKeybindings, toolsKeybindings, viewKeyBindings])
}


export const { KeybindsProvider, useKeybindAction, useKeybindShortcut } = makeKeybindsEnvironment(useAppKeybinds)
