import { useMemo } from "react"
import { Keybind } from "../../../common/components/keybindings"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { regionsSlice } from "./regionsSlice"

export function useToolsKeybindings() {
  const dispatch = useAppDispatch()
  const currentTool = useAppSelector(state => state.regions.tool)

  return useMemo(() => {
    const makeToggleTool = (tool: typeof currentTool, shortcut: string): Keybind => {
      return {
        action() {
          dispatch(regionsSlice.actions.toolChanged({ tool: currentTool === tool ? 'pan' : tool }))
        },
        shortcut,
      }
    }

    return {
      toggleLineTool: makeToggleTool('line', 'Shift+E'),
      toggleCircleTool: makeToggleTool('circle', 'Shift+C'),
      toggleRectTool: makeToggleTool('rect', 'Shift+R'),
      toggleTextTool: makeToggleTool('text', 'Shift+T'),
    }
  }, [dispatch, currentTool])
}
