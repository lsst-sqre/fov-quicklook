import { useMemo } from "react"
import { Keybind } from "../../../common/components/keybindings"
import { useAppDispatch } from "../../store/hooks"
import { catalogsSlice } from "../catalog/catalogSlice"
import { hipsLayersSlice } from "../hipsLayers/hipsLayersSlice"
import { regionsSlice } from "../regions/regionsSlice"
import { tractTileLayersSlice } from "../tractTileLayers/tractTileLayersSlice"
import { useAppContext } from "../../context"


export function useDialogsKeybindings() {
  const dispatch = useAppDispatch()
  const { dialogContext } = useAppContext()

  return useMemo(() => {
    const toggleToneDialog: Keybind = {
      action: () => {
        dispatch(tractTileLayersSlice.actions.toneDialogToggled({}))
      },
      shortcut: 'T',
    }
    const toggleRegionsDialog: Keybind = {
      action: () => {
        dispatch(regionsSlice.actions.regionsDialogToggled({}))
      },
      shortcut: 'R',
    }
    const toggleHipsDialog: Keybind = {
      action: () => {
        dispatch(hipsLayersSlice.actions.hipsDialogToggled({}))
      },
      shortcut: 'H',
    }
    const toggleCatalogsDialog: Keybind = {
      action: () => {
        dispatch(catalogsSlice.actions.catalogsDialogToggled({}))
      },
      shortcut: 'C',
    }
    const rearrangeDialogs: Keybind = {
      action: () => {
        dialogContext.current!.rearrange()
      },
      shortcut: 'A',
    }
    const closeAllDialogs: Keybind = {
      action: () => {
        dispatch(tractTileLayersSlice.actions.toneDialogToggled({ open: false }))
        dispatch(regionsSlice.actions.regionsDialogToggled({ open: false }))
        dispatch(hipsLayersSlice.actions.hipsDialogToggled({ open: false }))
        dispatch(catalogsSlice.actions.catalogsDialogToggled({ open: false }))
        dispatch(catalogsSlice.actions.dialogsClosed({}))
      },
      shortcut: 'X',
    }

    return {
      toggleToneDialog,
      toggleRegionsDialog,
      toggleHipsDialog,
      toggleCatalogsDialog,
      rearrangeDialogs,
      closeAllDialogs,
    }
  }, [dialogContext, dispatch])
}
