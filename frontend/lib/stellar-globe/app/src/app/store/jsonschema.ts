import { Slice } from "@reduxjs/toolkit"
import { BaseAction } from "../context"
import { appearanceLayersSlice } from "../features/appearanceLayers/appearanceLayersSlice"
import { cameraSlice } from "../features/camera/cameraSlice"
import { catalogsSlice } from "../features/catalog/catalogSlice"
import { commonSlice } from "../features/common/commonSlice"
import { develSlice } from "../features/devel/develSlice"
import { hipsLayersSlice } from "../features/hipsLayers/hipsLayersSlice"
import { regionsSlice } from "../features/regions/regionsSlice"
import { tractTileLayersSlice } from "../features/tractTileLayers/tractTileLayersSlice"
import { AppStateWithComputed } from "./computedState"
import { StorageState } from "./stateSync/StorageSync"
import { HashState } from "./stateSync/hashSync"
import type { FromApp, ToApp } from "../../../types/commTools"
import { fitsImageSlice } from "../features/fitsImage/fitsImageSlice"


export type PersistentStateJsonSchema = {
  HashState: HashState
  StorageState: StorageState
}


type AsAction<A> = A extends { type: string, payload: any } ? A : never
type PickAction<S extends Slice, K extends keyof S['actions']> = AsAction<ReturnType<S['actions'][K]>>
type ActionsNames<S extends Slice> = keyof S['actions']
type ActionsOfSlice<S extends Slice> = {
  [K in ActionsNames<S> as PickAction<S, K>['type']]: PickAction<S, K>
}
type ActionsWithValidatorOfSlice<S extends Slice> = {
  [K in ActionsNames<S> as PickAction<S, K>['type']]: PickAction<S, K>
}


export type ActionValidatorJsonSchema = {
  BaseAction: BaseAction
  Actions: (
    ActionsWithValidatorOfSlice<typeof commonSlice> &
    ActionsWithValidatorOfSlice<typeof appearanceLayersSlice> &
    ActionsWithValidatorOfSlice<typeof cameraSlice> &
    ActionsWithValidatorOfSlice<typeof tractTileLayersSlice> &
    ActionsWithValidatorOfSlice<typeof hipsLayersSlice> &
    ActionsWithValidatorOfSlice<typeof regionsSlice> &
    ActionsWithValidatorOfSlice<typeof catalogsSlice> &
    ActionsWithValidatorOfSlice<typeof develSlice> &
    ActionsWithValidatorOfSlice<typeof fitsImageSlice> &
    {}
  )
}


export type ToAppValidatorJsonSchema = {
  [K in keyof ToApp]: ToApp[K]
}


export type PublicJsonSchema = {
  // This type will be used in Python integration
  BaseAction: BaseAction
  StoreState: AppStateWithComputed
  Actions: (
    ActionsOfSlice<typeof commonSlice> &
    ActionsOfSlice<typeof appearanceLayersSlice> &
    ActionsOfSlice<typeof cameraSlice> &
    ActionsOfSlice<typeof tractTileLayersSlice> &
    ActionsOfSlice<typeof hipsLayersSlice> &
    ActionsOfSlice<typeof regionsSlice> &
    ActionsOfSlice<typeof catalogsSlice> &
    ActionsOfSlice<typeof develSlice> &
    ActionsOfSlice<typeof fitsImageSlice> &
    {}
  )
  ToApp: ToApp
  FromApp: FromApp
}
