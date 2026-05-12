import { baseApi as api } from "./base";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    getSystemInfo: build.query<GetSystemInfoApiResponse, GetSystemInfoApiArg>({
      query: () => ({ url: `/api/system_info` }),
    }),
    routeGetStatus: build.query<
      RouteGetStatusApiResponse,
      RouteGetStatusApiArg
    >({
      query: () => ({ url: `/api/status` }),
    }),
    healthz: build.query<HealthzApiResponse, HealthzApiArg>({
      query: () => ({ url: `/api/healthz` }),
    }),
    getTile: build.query<GetTileApiResponse, GetTileApiArg>({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/tiles/${queryArg.z}/${queryArg.y}/${queryArg.x}`,
      }),
    }),
    getFitsHeader: build.query<GetFitsHeaderApiResponse, GetFitsHeaderApiArg>({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/fits_header/${queryArg.ccdName}`,
      }),
    }),
    createQuicklook: build.mutation<
      CreateQuicklookApiResponse,
      CreateQuicklookApiArg
    >({
      query: (queryArg) => ({
        url: `/api/quicklooks`,
        method: "POST",
        body: queryArg.createQuicklookRequest,
      }),
    }),
    voteQuicklook: build.mutation<
      VoteQuicklookApiResponse,
      VoteQuicklookApiArg
    >({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/vote`,
        method: "POST",
      }),
    }),
    unvoteQuicklook: build.mutation<
      UnvoteQuicklookApiResponse,
      UnvoteQuicklookApiArg
    >({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/unvote`,
        method: "POST",
      }),
    }),
    getAllQuicklookJobs: build.query<
      GetAllQuicklookJobsApiResponse,
      GetAllQuicklookJobsApiArg
    >({
      query: () => ({ url: `/api/quicklooks/*/status` }),
    }),
    getQuicklookMetadata: build.query<
      GetQuicklookMetadataApiResponse,
      GetQuicklookMetadataApiArg
    >({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/quicklook_metadata`,
      }),
    }),
    getTimeProfile: build.query<
      GetTimeProfileApiResponse,
      GetTimeProfileApiArg
    >({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/time_profile`,
      }),
    }),
    listVisits: build.query<ListVisitsApiResponse, ListVisitsApiArg>({
      query: (queryArg) => ({
        url: `/api/visits`,
        params: {
          exposure: queryArg.exposure,
          day_obs: queryArg.dayObs,
          limit: queryArg.limit,
          data_type: queryArg.dataType,
          repository_name: queryArg.repositoryName,
        },
      }),
    }),
    listVisitDayCounts: build.query<
      ListVisitDayCountsApiResponse,
      ListVisitDayCountsApiArg
    >({
      query: (queryArg) => ({
        url: `/api/visits/day_counts`,
        params: {
          calendar_month: queryArg.calendarMonth,
          data_type: queryArg.dataType,
          repository_name: queryArg.repositoryName,
        },
      }),
    }),
    getVisitMetadata: build.query<
      GetVisitMetadataApiResponse,
      GetVisitMetadataApiArg
    >({
      query: (queryArg) => ({
        url: `/api/visits/${queryArg.visitName}/ccds/${queryArg.ccdName}`,
      }),
    }),
    getVisitResolution: build.query<
      GetVisitResolutionApiResponse,
      GetVisitResolutionApiArg
    >({
      query: (queryArg) => ({
        url: `/api/visits/${queryArg.visitName}/resolution`,
      }),
    }),
    getVisitRepresentativeUuid: build.query<
      GetVisitRepresentativeUuidApiResponse,
      GetVisitRepresentativeUuidApiArg
    >({
      query: (queryArg) => ({
        url: `/api/visits/${queryArg.visitName}/representative_uuid`,
      }),
    }),
    getExposureDataTypes: build.query<
      GetExposureDataTypesApiResponse,
      GetExposureDataTypesApiArg
    >({
      query: (queryArg) => ({ url: `/api/exposures/${queryArg.id}/types` }),
    }),
    getFitsFile: build.query<GetFitsFileApiResponse, GetFitsFileApiArg>({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.visitName}/fits/${queryArg.ccdName}`,
      }),
    }),
    killCoordinator: build.mutation<
      KillCoordinatorApiResponse,
      KillCoordinatorApiArg
    >({
      query: () => ({ url: `/api/admin/kill_coordinator`, method: "POST" }),
    }),
    killRandomGenerator: build.mutation<
      KillRandomGeneratorApiResponse,
      KillRandomGeneratorApiArg
    >({
      query: () => ({
        url: `/api/admin/kill_random_generator`,
        method: "POST",
      }),
    }),
    listCacheEntries: build.query<
      ListCacheEntriesApiResponse,
      ListCacheEntriesApiArg
    >({
      query: () => ({ url: `/api/cache_entries` }),
    }),
    deleteAllCacheEntries: build.mutation<
      DeleteAllCacheEntriesApiResponse,
      DeleteAllCacheEntriesApiArg
    >({
      query: () => ({ url: `/api/cache_entries/*`, method: "DELETE" }),
    }),
    deleteCacheEntry: build.mutation<
      DeleteCacheEntryApiResponse,
      DeleteCacheEntryApiArg
    >({
      query: (queryArg) => ({
        url: `/api/cache_entries/${queryArg.visitName}`,
        method: "DELETE",
      }),
    }),
    listStorageEntries: build.query<
      ListStorageEntriesApiResponse,
      ListStorageEntriesApiArg
    >({
      query: (queryArg) => ({
        url: `/api/storage`,
        params: {
          path: queryArg.path,
        },
      }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as api };
export type GetSystemInfoApiResponse =
  /** status 200 Successful Response */ SystemInfo;
export type GetSystemInfoApiArg = void;
export type RouteGetStatusApiResponse =
  /** status 200 Successful Response */ SystemStatus;
export type RouteGetStatusApiArg = void;
export type HealthzApiResponse = /** status 200 Successful Response */ any;
export type HealthzApiArg = void;
export type GetTileApiResponse = /** status 200 Successful Response */ any;
export type GetTileApiArg = {
  visitName: string;
  z: number;
  y: number;
  x: number;
};
export type GetFitsHeaderApiResponse =
  /** status 200 Successful Response */ HeaderType[];
export type GetFitsHeaderApiArg = {
  visitName: string;
  ccdName: string;
};
export type CreateQuicklookApiResponse =
  /** status 200 Successful Response */ any;
export type CreateQuicklookApiArg = {
  createQuicklookRequest: CreateQuicklookRequest;
};
export type VoteQuicklookApiResponse =
  /** status 200 Successful Response */ any;
export type VoteQuicklookApiArg = {
  visitName: string;
};
export type UnvoteQuicklookApiResponse =
  /** status 200 Successful Response */ any;
export type UnvoteQuicklookApiArg = {
  visitName: string;
};
export type GetAllQuicklookJobsApiResponse =
  /** status 200 Successful Response */ JobStatusList;
export type GetAllQuicklookJobsApiArg = void;
export type GetQuicklookMetadataApiResponse =
  /** status 200 Successful Response */ QuicklookMetadata;
export type GetQuicklookMetadataApiArg = {
  visitName: string;
};
export type GetTimeProfileApiResponse =
  /** status 200 Successful Response */ any;
export type GetTimeProfileApiArg = {
  visitName: string;
};
export type ListVisitsApiResponse =
  /** status 200 Successful Response */ VisitEntry[];
export type ListVisitsApiArg = {
  exposure?: number | null;
  dayObs?: number | null;
  limit?: number;
  dataType: string;
  repositoryName: string;
};
export type ListVisitDayCountsApiResponse =
  /** status 200 Successful Response */ VisitDayCount[];
export type ListVisitDayCountsApiArg = {
  calendarMonth: string;
  dataType: string;
  repositoryName: string;
};
export type GetVisitMetadataApiResponse =
  /** status 200 Successful Response */ DataSourceCcdMetadata;
export type GetVisitMetadataApiArg = {
  visitName: string;
  ccdName: string;
};
export type GetVisitResolutionApiResponse =
  /** status 200 Successful Response */ ResolvedVisitInfo;
export type GetVisitResolutionApiArg = {
  visitName: string;
};
export type GetVisitRepresentativeUuidApiResponse =
  /** status 200 Successful Response */ VisitRepresentativeUuid;
export type GetVisitRepresentativeUuidApiArg = {
  visitName: string;
};
export type GetExposureDataTypesApiResponse =
  /** status 200 Successful Response */ string[];
export type GetExposureDataTypesApiArg = {
  id: number;
};
export type GetFitsFileApiResponse = /** status 200 Successful Response */ any;
export type GetFitsFileApiArg = {
  visitName: string;
  ccdName: string;
};
export type KillCoordinatorApiResponse =
  /** status 200 Successful Response */ ShutdownResponse;
export type KillCoordinatorApiArg = void;
export type KillRandomGeneratorApiResponse =
  /** status 200 Successful Response */ KillGeneratorResponse;
export type KillRandomGeneratorApiArg = void;
export type ListCacheEntriesApiResponse =
  /** status 200 Successful Response */ CacheEntry[];
export type ListCacheEntriesApiArg = void;
export type DeleteAllCacheEntriesApiResponse =
  /** status 200 Successful Response */ any;
export type DeleteAllCacheEntriesApiArg = void;
export type DeleteCacheEntryApiResponse =
  /** status 200 Successful Response */ any;
export type DeleteCacheEntryApiArg = {
  visitName: string;
};
export type ListStorageEntriesApiResponse =
  /** status 200 Successful Response */ Entry[];
export type ListStorageEntriesApiArg = {
  path: string;
};
export type ContextMenuTemplate = {
  name: string;
  template: string;
  is_url: boolean;
};
export type CcdDataTypeConfig = {
  data_type: string;
  display_name: string;
  collections: string[];
  data_id_dimension?: string;
  order_by?: string[];
  partial?: boolean;
  repository_name?: string;
  instrument?: string;
};
export type SystemInfo = {
  admin_page: boolean;
  context_menu_templates: ContextMenuTemplate[];
  max_object_storage_usage: number;
  ccd_data_types: CcdDataTypeConfig[];
};
export type MemoryStats = {
  /** Anonymous memory usage in bytes (private memory not backed by files) */
  anon: number;
  /** File-backed memory usage in bytes (page cache) */
  file: number;
  /** Kernel memory usage in bytes */
  kernel: number;
  /** Slab memory usage in bytes (kernel data structures) */
  slab: number;
  /** Socket buffer memory usage in bytes */
  sock: number;
  /** Shared memory usage in bytes */
  shmem: number;
  /** Memory-mapped file pages in bytes */
  file_mapped: number;
  /** Dirty file-backed pages waiting to be written in bytes */
  file_dirty: number;
  /** File-backed pages currently being written back in bytes */
  file_writeback: number;
  /** Inactive anonymous memory in bytes (candidates for swapping) */
  inactive_anon: number;
  /** Active anonymous memory in bytes (recently accessed) */
  active_anon: number;
  /** Inactive file-backed memory in bytes (candidates for reclaim) */
  inactive_file: number;
  /** Active file-backed memory in bytes (recently accessed) */
  active_file: number;
  /** Unevictable memory in bytes (locked, cannot be swapped) */
  unevictable: number;
};
export type ContainerStatus = {
  /** Container hostname */
  container_name: string;
  /** Memory limit in bytes (0 if unlimited) */
  memory_max: number;
  /** Current total memory usage in bytes */
  memory_current: number;
  /** Detailed memory breakdown from cgroup memory.stat */
  memory_stats: MemoryStats | null;
  /** CPU quota in microseconds per period (0 if unlimited) */
  cpu_max: number;
  /** Accumulated CPU usage time in microseconds since container start */
  cpu_current: number;
  /** Container uptime in seconds since boot */
  uptime: number;
};
export type SystemStatus = {
  frontend: ContainerStatus;
  coordinator: ContainerStatus;
  generators: {
    [key: string]: ContainerStatus;
  };
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type CardType = [string, string, string, string];
export type HeaderType = CardType[];
export type CreateQuicklookRequest = {
  visit: string;
};
export type Job = {
  visit: string;
  id?: string;
};
export type Progress = {
  total: number;
  count?: number;
};
export type JobStatus = {
  job: Job;
  stage?:
    | "queued"
    | "generate_single_fits_tiles"
    | "merge_tiles"
    | "upload_to_object_storage"
    | "ready"
    | "error";
  generate_single_fits_tiles?: {
    [key: string]: Progress;
  };
  merge_tiles?: {
    [key: string]: Progress;
  };
  transfer_tiles?: {
    [key: string]: Progress;
  };
  error_message?: string | null;
};
export type JobStatusList = {
  [key: string]: JobStatus;
};
export type ImageStat = {
  median: number | null;
  mad: number | null;
  shape: number[];
};
export type BBox = {
  miny: number;
  maxy: number;
  minx: number;
  maxx: number;
};
export type AmpMetadata = {
  amp_id: number;
  bbox: BBox;
};
export type CcdMetadata = {
  ccd_name: string;
  image_stat: ImageStat;
  amps: AmpMetadata[];
  bbox: BBox;
};
export type QuicklookMetadataReady = {
  visit_name: string;
  ccd_metadata_list: CcdMetadata[];
  wcs: {
    [key: string]: any;
  };
  type?: "ready";
};
export type QuicklookMetadataProgress = {
  visit_name: string;
  progress: {
    [key: string]: Progress;
  };
  type?: "progress";
};
export type QuicklookMetadataPending = {
  visit_name: string;
  type?: "pending";
};
export type QuicklookMetadataError = {
  visit_name: string;
  type?: "error";
};
export type QuicklookMetadata =
  | QuicklookMetadataReady
  | QuicklookMetadataProgress
  | QuicklookMetadataPending
  | QuicklookMetadataError;
export type VisitEntry = {
  id: string;
  day_obs: number;
  physical_filter: string;
  obs_id: string;
  exposure_time: number;
  science_program: string;
  observation_type: string;
  observation_reason: string;
  target_name: string;
  uuid?: string | null;
};
export type VisitDayCount = {
  day_obs: number;
  count: number;
};
export type DataSourceCcdMetadata = {
  visit_name: string;
  ccd_name: string;
  detector: number;
  exposure: number;
  day_obs: number;
  uuid: string;
};
export type ResolvedVisitInfo = {
  visit_name: string;
  detector?: number | null;
};
export type VisitRepresentativeUuid = {
  uuid: string;
};
export type ShutdownResponse = {
  status: string;
};
export type KillGeneratorResponse = {
  status: string;
  generator_id: string;
};
export type CacheEntry = {
  visit_name: string;
  ready: boolean;
  created_at: string;
  disk_usage: number;
};
export type Entry = {
  name: string;
  type: "directory" | "file";
  size: number | null;
};
export const {
  useGetSystemInfoQuery,
  useRouteGetStatusQuery,
  useHealthzQuery,
  useGetTileQuery,
  useGetFitsHeaderQuery,
  useCreateQuicklookMutation,
  useVoteQuicklookMutation,
  useUnvoteQuicklookMutation,
  useGetAllQuicklookJobsQuery,
  useGetQuicklookMetadataQuery,
  useGetTimeProfileQuery,
  useListVisitsQuery,
  useListVisitDayCountsQuery,
  useGetVisitMetadataQuery,
  useGetVisitResolutionQuery,
  useGetVisitRepresentativeUuidQuery,
  useGetExposureDataTypesQuery,
  useGetFitsFileQuery,
  useKillCoordinatorMutation,
  useKillRandomGeneratorMutation,
  useListCacheEntriesQuery,
  useDeleteAllCacheEntriesMutation,
  useDeleteCacheEntryMutation,
  useListStorageEntriesQuery,
} = injectedRtkApi;
