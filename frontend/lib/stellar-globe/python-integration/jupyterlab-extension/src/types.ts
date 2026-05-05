import { JupyterFrontEnd } from '@jupyterlab/application'
import { ISessionContext } from '@jupyterlab/apputils'

export type KernelType = NonNullable<NonNullable<ISessionContext['session']>['kernel']>
export type StellarGlobeSessionEnv = {
  kernel: KernelType
  app: JupyterFrontEnd
}
export type CommType = Parameters<Parameters<KernelType['registerCommTarget']>[1]>[0]

