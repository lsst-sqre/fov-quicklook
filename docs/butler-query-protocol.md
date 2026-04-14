# Butler Query URL Protocol

This document describes the URL-driven Butler search flow that is available in the frontend and backend.

## Frontend page

The frontend exposes a read-only query results page at:

```text
/query
```

The page has no dedicated search form. Instead, it reads the current URL search parameters, forwards them to the backend Butler query API, and renders the returned records as a table.

Example:

```text
/query?data_type=raw&day_obs=20260503&limit=10
```

When the application is served under the default frontend prefix, the full browser URL is:

```text
/fov-quicklook/query?data_type=raw&day_obs=20260503&limit=10
```

## Backend APIs

### 1. Query records

```text
GET /api/butler/query
```

Reserved query parameters:

| Parameter | Required | Meaning |
| --- | --- | --- |
| `data_type` | Yes | Butler dataset type name, such as `raw` or `difference_image` |
| `repository_name` | No | Butler repository name. Omit it when the dataset type is configured for exactly one repository |
| `collection` | No | Collection override. May be repeated or passed as a comma-separated list |
| `limit` | No | Page size. Default: `100`, maximum: `1000` |
| `offset` | No | Zero-based result offset. Default: `0` |
| `order` | No | Sort order. May be repeated or passed as a comma-separated list. Use Butler field names, for example `-day_obs,-exposure` |

All other query parameters are treated as Butler dimension filters and are joined with `and`.

Examples:

```text
/api/butler/query?data_type=raw&day_obs=20260503&limit=10
/api/butler/query?data_type=raw&day_obs=20260503&physical_filter=g&order=-day_obs,-exposure
/api/butler/query?data_type=difference_image&visit=12345&collection=LSSTCam/runs/nightlyValidation
```

Filter alias:

| Alias | Normalized Butler field |
| --- | --- |
| `filter` | `physical_filter` |

The response contains:

- dataset metadata (`repository_name`, `data_type`, `data_id_dimension`)
- the normalized filters, collections, and ordering that were applied
- paging state (`limit`, `offset`, `returned_count`, `has_more`)
- `columns`: the suggested display order for table columns
- `rows`: each row contains a `visit_name` and a generic `record` object

`visit_name` can be linked directly to the existing quicklook viewer at `/visits/{visit_name}`.

### 2. List configured dataset types

```text
GET /api/butler/dataset_types
```

Optional query parameter:

| Parameter | Meaning |
| --- | --- |
| `repository_name` | Restrict the returned dataset types to one repository |

This endpoint returns the configured dataset types, display names, default collections, and default ordering.

### 3. Describe dataset dimensions

```text
GET /api/butler/dataset_types/{data_type}/dimensions
```

Optional query parameter:

| Parameter | Meaning |
| --- | --- |
| `repository_name` | Required only when the same dataset type exists in multiple configured repositories |

This endpoint returns:

- `data_id_dimension`
- Butler dataset dimensions for the dataset type
- supported filter aliases

## Notes

- The query endpoint is additive. Existing `/api/visits` behavior is unchanged.
- `offset` is applied after the Butler result set is ordered.
- `has_more=true` means more rows are available beyond the current page.
- If `repository_name` is omitted for an ambiguous `data_type`, the backend returns `400 Bad Request`.
