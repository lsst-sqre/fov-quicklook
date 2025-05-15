import { baseApi as api } from "./base";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    getSystemInfo: build.query<GetSystemInfoApiResponse, GetSystemInfoApiArg>({
      query: () => ({ url: `/api/system_info` }),
    }),
    healthz: build.query<HealthzApiResponse, HealthzApiArg>({
      query: () => ({ url: `/api/healthz` }),
    }),
    ready: build.query<ReadyApiResponse, ReadyApiArg>({
      query: () => ({ url: `/api/ready` }),
    }),
    getTile: build.query<GetTileApiResponse, GetTileApiArg>({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.id}/tiles/${queryArg.z}/${queryArg.y}/${queryArg.x}`,
      }),
    }),
    getFitsHeader: build.query<GetFitsHeaderApiResponse, GetFitsHeaderApiArg>({
      query: (queryArg) => ({
        url: `/api/quicklooks/${queryArg.id}/fits_header/${queryArg.ccdName}`,
      }),
    }),
    showQuicklookStatus: build.query<
      ShowQuicklookStatusApiResponse,
      ShowQuicklookStatusApiArg
    >({
      query: (queryArg) => ({ url: `/api/quicklooks/${queryArg.id}/status` }),
    }),
    showQuicklookMetadata: build.query<
      ShowQuicklookMetadataApiResponse,
      ShowQuicklookMetadataApiArg
    >({
      query: (queryArg) => ({ url: `/api/quicklooks/${queryArg.id}/metadata` }),
    }),
    deleteAllQuicklooks: build.mutation<
      DeleteAllQuicklooksApiResponse,
      DeleteAllQuicklooksApiArg
    >({
      query: () => ({ url: `/api/quicklooks/*`, method: "DELETE" }),
    }),
    createQuicklook: build.mutation<
      CreateQuicklookApiResponse,
      CreateQuicklookApiArg
    >({
      query: (queryArg) => ({
        url: `/api/quicklooks`,
        method: "POST",
        body: queryArg.quicklookCreateFrontend,
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
        },
      }),
    }),
    getVisitMetadata: build.query<
      GetVisitMetadataApiResponse,
      GetVisitMetadataApiArg
    >({
      query: (queryArg) => ({
        url: `/api/visits/${queryArg.id}/ccds/${queryArg.ccdName}`,
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
        url: `/api/quicklooks/${queryArg.id}/fits/${queryArg.ccdName}`,
      }),
    }),
    getPodStatus: build.query<GetPodStatusApiResponse, GetPodStatusApiArg>({
      query: () => ({ url: `/api/status` }),
    }),
    listCacheEntries: build.query<
      ListCacheEntriesApiResponse,
      ListCacheEntriesApiArg
    >({
      query: () => ({ url: `/api/cache_entries` }),
    }),
    cleanupCacheEntries: build.mutation<
      CleanupCacheEntriesApiResponse,
      CleanupCacheEntriesApiArg
    >({
      query: () => ({ url: `/api/cache_entries:cleanup`, method: "POST" }),
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
    deleteStorageEntry: build.mutation<
      DeleteStorageEntryApiResponse,
      DeleteStorageEntryApiArg
    >({
      query: (queryArg) => ({
        url: `/api/storage`,
        method: "DELETE",
        params: {
          path: queryArg.path,
        },
      }),
    }),
    deleteStorageEntriesByPrefix: build.mutation<
      DeleteStorageEntriesByPrefixApiResponse,
      DeleteStorageEntriesByPrefixApiArg
    >({
      query: (queryArg) => ({
        url: `/api/storage/by-prefix`,
        method: "DELETE",
        params: {
          prefix: queryArg.prefix,
        },
      }),
    }),
    listHipsRepositories: build.query<
      ListHipsRepositoriesApiResponse,
      ListHipsRepositoriesApiArg
    >({
      query: () => ({ url: `/api/hips` }),
    }),
    getHipsFile: build.query<GetHipsFileApiResponse, GetHipsFileApiArg>({
      query: (queryArg) => ({ url: `/api/hips/${queryArg.path}` }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as api };
export type GetSystemInfoApiResponse =
  /** status 200 Successful Response */ SystemInfo;
export type GetSystemInfoApiArg = void;
export type HealthzApiResponse = /** status 200 Successful Response */ any;
export type HealthzApiArg = void;
export type ReadyApiResponse = /** status 200 Successful Response */ any;
export type ReadyApiArg = void;
export type GetTileApiResponse = /** status 200 Successful Response */ any;
export type GetTileApiArg = {
  z: number;
  y: number;
  x: number;
  id: string;
};
export type GetFitsHeaderApiResponse =
  /** status 200 Successful Response */ HeaderType[];
export type GetFitsHeaderApiArg = {
  ccdName: string;
  id: string;
};
export type ShowQuicklookStatusApiResponse =
  /** status 200 Successful Response */ QuicklookStatus | null;
export type ShowQuicklookStatusApiArg = {
  id: string;
};
export type ShowQuicklookMetadataApiResponse =
  /** status 200 Successful Response */ QuicklookMetadata;
export type ShowQuicklookMetadataApiArg = {
  id: string;
};
export type DeleteAllQuicklooksApiResponse =
  /** status 200 Successful Response */ any;
export type DeleteAllQuicklooksApiArg = void;
export type CreateQuicklookApiResponse =
  /** status 200 Successful Response */ any;
export type CreateQuicklookApiArg = {
  quicklookCreateFrontend: QuicklookCreateFrontend;
};
export type ListVisitsApiResponse =
  /** status 200 Successful Response */ VisitEntry[];
export type ListVisitsApiArg = {
  exposure?: number | null;
  dayObs?: number | null;
  limit?: number;
  dataType?: "raw" | "post_isr_image" | "preliminary_visit_image";
};
export type GetVisitMetadataApiResponse =
  /** status 200 Successful Response */ DataSourceCcdMetadata;
export type GetVisitMetadataApiArg = {
  id: string;
  ccdName: string;
};
export type GetExposureDataTypesApiResponse =
  /** status 200 Successful Response */ (
    | "raw"
    | "post_isr_image"
    | "preliminary_visit_image"
  )[];
export type GetExposureDataTypesApiArg = {
  id: number;
};
export type GetFitsFileApiResponse = /** status 200 Successful Response */ any;
export type GetFitsFileApiArg = {
  ccdName: string;
  id: string;
};
export type GetPodStatusApiResponse =
  /** status 200 Successful Response */ StatusResponse;
export type GetPodStatusApiArg = void;
export type ListCacheEntriesApiResponse =
  /** status 200 Successful Response */ CacheEntry[];
export type ListCacheEntriesApiArg = void;
export type CleanupCacheEntriesApiResponse =
  /** status 200 Successful Response */ any;
export type CleanupCacheEntriesApiArg = void;
export type ListStorageEntriesApiResponse =
  /** status 200 Successful Response */ Entry[];
export type ListStorageEntriesApiArg = {
  path: string;
};
export type DeleteStorageEntryApiResponse =
  /** status 200 Successful Response */ any;
export type DeleteStorageEntryApiArg = {
  path: string;
};
export type DeleteStorageEntriesByPrefixApiResponse =
  /** status 200 Successful Response */ any;
export type DeleteStorageEntriesByPrefixApiArg = {
  prefix: string;
};
export type ListHipsRepositoriesApiResponse =
  /** status 200 Successful Response */ HipsRepository[];
export type ListHipsRepositoriesApiArg = void;
export type GetHipsFileApiResponse = /** status 200 Successful Response */ any;
export type GetHipsFileApiArg = {
  path: string;
};
export type SystemInfo = {
  admin_page?: boolean;
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
export type QuicklookJobPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | -1;
export type Progress = {
  count: number;
  total: number;
};
export type GenerateProgress = {
  download: Progress;
  preprocess: Progress;
  maketile: Progress;
};
export type TransferProgress = {
  transfer: Progress;
};
export type MergeProgress = {
  merge: Progress;
};
export type QuicklookStatus = {
  id: string;
  phase: QuicklookJobPhase;
  generate_progress: {
    [key: string]: GenerateProgress;
  } | null;
  transfer_progress: {
    [key: string]: TransferProgress;
  } | null;
  merge_progress: {
    [key: string]: MergeProgress;
  } | null;
};
export type Visit = {
  id: string;
};
export type CcdId = {
  visit: Visit;
  ccd_name: string;
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
export type AmpMeta = {
  amp_id: number;
  bbox: BBox;
};
export type CcdMeta = {
  ccd_id: CcdId;
  image_stat: ImageStat;
  amps: AmpMeta[];
  bbox: BBox;
};
export type QuicklookMetadata = {
  id: string;
  wcs: object;
  ccd_meta: CcdMeta[] | null;
};
export type QuicklookCreateFrontend = {
  id: string;
};
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
};
export type DataSourceCcdMetadata = {
  visit: Visit;
  ccd_name: string;
  detector: number;
  exposure: number;
  day_obs: number;
  uuid: string;
};
export type DiskInfo = {
  mount_point: string;
  total: number;
  used: number;
  device: string;
};
export type PodStatus = {
  hostname: string;
  ip_addr: string;
  memory_total: number;
  memory_used: number;
  disks: DiskInfo[];
};
export type StatusResponse = {
  frontend: PodStatus;
  coordinator: PodStatus;
  generators: PodStatus[];
};
export type CacheEntry = {
  id: string;
  phase: "ready" | "in_progress" | "deleting";
  created_at: string;
  updated_at: string;
};
export type Entry = {
  name: string;
  type: "directory" | "file";
  size: number | null;
};
export type HipsRepository = {
  name: string;
};
export const {
  useGetSystemInfoQuery,
  useHealthzQuery,
  useReadyQuery,
  useGetTileQuery,
  useGetFitsHeaderQuery,
  useShowQuicklookStatusQuery,
  useShowQuicklookMetadataQuery,
  useDeleteAllQuicklooksMutation,
  useCreateQuicklookMutation,
  useListVisitsQuery,
  useGetVisitMetadataQuery,
  useGetExposureDataTypesQuery,
  useGetFitsFileQuery,
  useGetPodStatusQuery,
  useListCacheEntriesQuery,
  useCleanupCacheEntriesMutation,
  useListStorageEntriesQuery,
  useDeleteStorageEntryMutation,
  useDeleteStorageEntriesByPrefixMutation,
  useListHipsRepositoriesQuery,
  useGetHipsFileQuery,
} = injectedRtkApi;
