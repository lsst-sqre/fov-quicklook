import { baseApi as api } from "./base";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    getSystemInfo: build.query<GetSystemInfoApiResponse, GetSystemInfoApiArg>({
      query: () => ({ url: `/api/system_info` }),
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
        url: `/api/visits/${queryArg.visitName}/ccds/${queryArg.ccdName}`,
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
  }),
  overrideExisting: false,
});
export { injectedRtkApi as api };
export type GetSystemInfoApiResponse =
  /** status 200 Successful Response */ SystemInfo;
export type GetSystemInfoApiArg = void;
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
export type GetAllQuicklookJobsApiResponse =
  /** status 200 Successful Response */ JobStatusList;
export type GetAllQuicklookJobsApiArg = void;
export type GetQuicklookMetadataApiResponse =
  /** status 200 Successful Response */ QuicklookMetadata;
export type GetQuicklookMetadataApiArg = {
  visitName: string;
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
  visitName: string;
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
  visitName: string;
  ccdName: string;
};
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
export type ContextMenuTemplate = {
  name: string;
  template: string;
  is_url: boolean;
};
export type SystemInfo = {
  admin_page: boolean;
  context_menu_templates: ContextMenuTemplate[];
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
    | "transfer_fits_headers"
    | "transfer_tiles"
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
export type QuicklookMetadataError = {
  visit_name: string;
  type?: "error";
};
export type QuicklookMetadata =
  | QuicklookMetadataReady
  | QuicklookMetadataProgress
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
};
export type DataSourceCcdMetadata = {
  visit_name: string;
  ccd_name: string;
  detector: number;
  exposure: number;
  day_obs: number;
  uuid: string;
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
  useHealthzQuery,
  useGetTileQuery,
  useGetFitsHeaderQuery,
  useCreateQuicklookMutation,
  useGetAllQuicklookJobsQuery,
  useGetQuicklookMetadataQuery,
  useListVisitsQuery,
  useGetVisitMetadataQuery,
  useGetExposureDataTypesQuery,
  useGetFitsFileQuery,
  useListCacheEntriesQuery,
  useDeleteAllCacheEntriesMutation,
  useDeleteCacheEntryMutation,
  useListStorageEntriesQuery,
  useDeleteStorageEntryMutation,
  useDeleteStorageEntriesByPrefixMutation,
} = injectedRtkApi;
