import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import { env } from '../../env'
import type { JobStatusList, QuicklookMetadata } from './openapi'

export const baseApi = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: env.baseUrl }),
  endpoints: (build) => ({
    getQuicklooksStatus: build.query<JobStatusList, void>({
      queryFn: () => ({ data: {} }),
      async onCacheEntryAdded(
        _arg,
        { updateCachedData, cacheDataLoaded, cacheEntryRemoved }
      ) {
        const wsUrl = env.baseUrl.replace(/^http/, 'ws') + '/api/quicklooks/*/status.ws'
        const ws = new WebSocket(wsUrl)

        try {
          await cacheDataLoaded

          const listener = (event: MessageEvent) => {
            const data = JSON.parse(event.data) as JobStatusList
            updateCachedData(() => data)
          }

          ws.addEventListener('message', listener)
        } catch {
        }

        await cacheEntryRemoved
        ws.close()
      },
    }),
    getQuicklookMetadata_WS_: build.query<QuicklookMetadata | undefined, { visitName: string }>({
      queryFn: () => ({ data: undefined }),
      async onCacheEntryAdded(
        arg,
        { updateCachedData, cacheDataLoaded, cacheEntryRemoved }
      ) {
        const wsUrl = env.baseUrl.replace(/^http/, 'ws') + `/api/quicklooks/${arg.visitName}/quicklook_metadata.ws`
        const ws = new WebSocket(wsUrl)

        try {
          await cacheDataLoaded

          const listener = (event: MessageEvent) => {
            console.log(event.data)
            const data = JSON.parse(event.data) as QuicklookMetadata
            updateCachedData(() => data)
          }

          ws.addEventListener('message', listener)
        } catch {
        }

        await cacheEntryRemoved
        ws.close()
      },
    }),
  }),
})

export const {
  useGetQuicklooksStatusQuery,
  useGetQuicklookMetadata_WS_Query,
} = baseApi
