import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { EndpointBuilder } from '@reduxjs/toolkit/query'
import { env } from '../../env'
import type { JobStatusList, QuicklookMetadata, SystemStatus } from './openapi'

type BaseQueryFn = ReturnType<typeof fetchBaseQuery>

function wsQueryEndpoint<TData, TArg>(
  build: EndpointBuilder<BaseQueryFn, never, 'api'>,
  initialData: TData,
  buildPath: (arg: TArg) => string,
) {
  return build.query<TData, TArg>({
    queryFn: () => ({ data: initialData }),
    async onCacheEntryAdded(
      arg,
      { updateCachedData, cacheDataLoaded, cacheEntryRemoved },
    ) {
      const wsUrl = env.baseUrl.replace(/^http/, 'ws') + buildPath(arg)
      const ws = new WebSocket(wsUrl)

      try {
        await cacheDataLoaded

        ws.addEventListener('message', (event: MessageEvent) => {
          const data = JSON.parse(event.data) as TData
          updateCachedData(() => data)
        })
      } catch {
      }

      await cacheEntryRemoved
      ws.close()
    },
  })
}

export const baseApi = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: env.baseUrl }),
  endpoints: (build) => ({
    getQuicklooksStatus: wsQueryEndpoint<JobStatusList, void>(
      build, {} as JobStatusList, () => '/api/quicklooks/*/status.ws',
    ),
    getQuicklookMetadata_WS_: wsQueryEndpoint<QuicklookMetadata | undefined, { visitName: string }>(
      build, undefined, (arg) => `/api/quicklooks/${arg.visitName}/quicklook_metadata.ws`,
    ),
    getSystemStatus_WS_: wsQueryEndpoint<SystemStatus | undefined, void>(
      build, undefined, () => '/api/status/ws',
    ),
  }),
})

export const {
  useGetQuicklooksStatusQuery,
  useGetQuicklookMetadata_WS_Query,
  useGetSystemStatus_WS_Query,
} = baseApi
