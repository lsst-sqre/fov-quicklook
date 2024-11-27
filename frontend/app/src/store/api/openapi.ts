import { baseApi as api } from "./base";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    healthz: build.query<HealthzApiResponse, HealthzApiArg>({
      query: () => ({ url: `/api/healthz` }),
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
    listQuicklooks: build.query<
      ListQuicklooksApiResponse,
      ListQuicklooksApiArg
    >({
      query: () => ({ url: `/api/quicklooks` }),
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
    listVisits: build.query<ListVisitsApiResponse, ListVisitsApiArg>({
      query: () => ({ url: `/api/visits` }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as api };
export type HealthzApiResponse = /** status 200 Successful Response */ any;
export type HealthzApiArg = void;
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
export type ListQuicklooksApiResponse =
  /** status 200 Successful Response */ QuicklookStatus[];
export type ListQuicklooksApiArg = void;
export type CreateQuicklookApiResponse =
  /** status 200 Successful Response */ any;
export type CreateQuicklookApiArg = {
  quicklookCreateFrontend: QuicklookCreateFrontend;
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
export type ListVisitsApiResponse =
  /** status 200 Successful Response */ VisitListEntry[];
export type ListVisitsApiArg = void;
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
export type Progress = {
  count: number;
  total: number;
};
export type GeneratorProgress = {
  download: Progress;
  preprocess: Progress;
  maketile: Progress;
};
export type Visit = {
  data_type: "raw" | "calexp";
  name: string;
};
export type CcdId = {
  visit: Visit;
  ccd_name: string;
};
export type ImageStat = {
  median: number;
  mad: number;
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
export type QuicklookMeta = {
  ccd_meta: CcdMeta[];
};
export type QuicklookStatus = {
  id: string;
  phase: "queued" | "processing" | "ready" | "deleting";
  generating_progress: {
    [key: string]: GeneratorProgress;
  } | null;
  meta: QuicklookMeta | null;
};
export type QuicklookCreateFrontend = {
  id: string;
};
export type QuicklookMetadata = {
  id: string;
  wcs: object;
  ccd_meta: CcdMeta[] | null;
};
export type VisitListEntry = {
  name: string;
};
export const {
  useHealthzQuery,
  useGetTileQuery,
  useGetFitsHeaderQuery,
  useListQuicklooksQuery,
  useCreateQuicklookMutation,
  useShowQuicklookStatusQuery,
  useShowQuicklookMetadataQuery,
  useDeleteAllQuicklooksMutation,
  useListVisitsQuery,
} = injectedRtkApi;
