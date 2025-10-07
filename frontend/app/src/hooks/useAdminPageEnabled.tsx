import { useGetSystemInfoQuery } from "../store/api/openapi"

export function useAdminPageEnabled() {
  const { data } = useGetSystemInfoQuery()
  return data?.admin_page
}
