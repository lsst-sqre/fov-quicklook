import { env } from "./env"
import { SystemInfo } from "./store/api/openapi"


let systemInfoCache: SystemInfo | null = null

export async function getSystemInfo() {
  if (systemInfoCache) {
    return systemInfoCache
  }
  const response = await fetch(`${env.baseUrl}/api/system_info`)
  if (!response.ok) {
    throw new Error('Failed to fetch system info')
  }
  systemInfoCache = await response.json() as SystemInfo
  return systemInfoCache
}

export function getSystemInfoSync() {
  if (systemInfoCache) {
    return systemInfoCache
  }
  throw new Error('System info not yet fetched. Use getSystemInfo() to fetch it asynchronously.')
}
