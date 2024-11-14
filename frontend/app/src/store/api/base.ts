import { FetchBaseQueryError, createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
// import { paths } from '../../../openapi.json'

export const baseApi = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: '.' }),
  endpoints: () => ({}),
})

// export function apiEndpoint<P extends keyof typeof paths, M extends keyof typeof paths[P]>(path: P, method: M) {
//   return [`.${path}`, method] as const
// }

export function isFetchBaseQueryError(error: any): error is FetchBaseQueryError {
  return typeof error === 'object' && error !== null && 'status' in error
}

export function errorSummary(e: FetchBaseQueryError): string {
  if (typeof e.data === 'string') {
    return e.data
  }
  // @ts-ignore
  const detail: any = e.data.detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => {
      return d.msg ?? JSON.stringify(d)
    }).join('\n')
  }
  if (typeof detail === 'string') {
    return detail
  }
  return JSON.stringify(e.data, null, 2)
}
