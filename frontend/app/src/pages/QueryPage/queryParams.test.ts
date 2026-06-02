import { describe, expect, it } from "vitest"
import { buildByUuidVisitName, buildDefaultQueryInput, buildQueryPythonSnippet, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

describe("query params helpers", () => {
  it("normalizes an optional /query prefix", () => {
    expect(normalizeQueryInput("/query?data_type=raw&repository_name=embargo")).toBe("data_type=raw&repository_name=embargo")
    expect(normalizeQueryInput("?data_type=raw")).toBe("data_type=raw")
  })

  it("builds list visit arguments from the URL search params", () => {
    const result = buildVisitListArgs(new URLSearchParams("repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=2&offset=1000&where=day_obs=20260128"))

    expect(result).toEqual({
      args: {
        repositoryName: "embargo",
        collection: "LSSTCam/raw/all",
        datasetType: "raw",
        limit: 2,
        offset: 1000,
        where: "day_obs=20260128",
        reverse: undefined,
      },
      error: null,
    })
  })

  it("omits missing optional query params from the visit args", () => {
    const result = buildVisitListArgs(new URLSearchParams("repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"))

    expect(result).toEqual({
      args: {
        repositoryName: "embargo",
        collection: "LSSTCam/raw/all",
        datasetType: "raw",
        limit: 100,
        reverse: undefined,
      },
      error: null,
    })
  })

  it("reports invalid integer parameters", () => {
    expect(buildVisitListArgs(new URLSearchParams("repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=two"))).toEqual({
      args: null,
      error: "limit must be an integer.",
    })
  })

  it("builds a by_uuid visit name", () => {
    expect(buildByUuidVisitName("embargo:LSSTCam!-runs!-nightlyValidation:difference_image:visit=7001", "uuid-1")).toBe("embargo:by_uuid:uuid-1")
  })

  it("builds a default query string from the current datasource", () => {
    expect(buildDefaultQueryInput("main:LSSTCam!-raw!-all:raw")).toBe("repository_name=main&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=100")
    expect(buildDefaultQueryInput("embargo:LSSTCam!-runs!-nightlyValidation:difference_image", 5)).toBe("repository_name=embargo&collection=LSSTCam%2Fruns%2FnightlyValidation&dataset_type=difference_image&limit=5")
  })

  it("builds runnable python code from the current query string", () => {
    expect(
      buildQueryPythonSnippet(
        "repository_name=embargo&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=100",
      ),
    ).toBe(
      "import os\n"
      + "import shutil\n"
      + "import stat\n"
      + "import tempfile\n\n"
      + "from itertools import islice\n"
      + "from urllib.parse import parse_qs\n\n"
      + "from lsst.daf.butler import Butler\n\n"
      + "def prepare_pgpass() -> None:\n"
      + "    if pgpass := os.environ.get('PGPASSFILE'):\n"
      + "        fd, temp_path = tempfile.mkstemp(prefix='.pgpass_')\n"
      + "        os.close(fd)\n"
      + "        shutil.copyfile(pgpass, temp_path)\n"
      + "        os.chmod(temp_path, stat.S_IRUSR)\n"
      + "        os.environ['PGPASSFILE'] = temp_path\n\n"
      + "def quicklook_dimension(dataset_type: str) -> str:\n"
      + "    if dataset_type in {'difference_image', 'preliminary_visit_image'}:\n"
      + "        return 'visit'\n"
      + "    return 'exposure'\n\n"
      + "def default_order_by(dataset_type: str) -> str:\n"
      + "    return {\n"
      + "        'raw': '-day_obs',\n"
      + "        'post_isr_image': '-exposure',\n"
      + "        'difference_image': '-visit',\n"
      + "        'preliminary_visit_image': '-visit',\n"
      + "        'calexp': '-exposure',\n"
      + "    }.get(dataset_type, '-exposure')\n\n"
      + "def normalize_order_by(dataset_type: str, order_by: str | None, reverse: bool | None) -> list[str]:\n"
      + "    default = default_order_by(dataset_type)\n"
      + "    selected_field = order_by or default.removeprefix('-')\n"
      + "    selected_reverse = default.startswith('-') if reverse is None else reverse\n"
      + "    prefix = '-' if selected_reverse else ''\n"
      + "    return [f'{prefix}{selected_field}']\n\n"
      + "prepare_pgpass()\n\n"
      + "query_string = 'repository_name=embargo&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw&limit=100'\n"
      + "params = {key: values[-1] for key, values in parse_qs(query_string).items()}\n\n"
      + "repository_name = params['repository_name']\n"
      + "collection = params['collection']\n"
      + "dataset_type = params['dataset_type']\n"
      + "where = params.get('where')\n"
      + "order_by = params.get('order_by')\n"
      + "reverse = None if 'reverse' not in params else params['reverse'].lower() == 'true'\n"
      + "limit = int(params['limit']) if 'limit' in params else 100\n"
      + "offset = int(params['offset']) if 'offset' in params else 0\n\n"
      + "butler = Butler(repository_name, instrument='LSSTCam', collections=[collection])\n"
      + "dimension = quicklook_dimension(dataset_type)\n"
      + "query_kwargs = {'datasets': dataset_type}\n"
      + "if dataset_type == 'difference_image':\n"
      + "    query_kwargs['collections'] = ...\n"
      + "if where:\n"
      + "    query_kwargs['where'] = where\n"
      + "else:\n"
      + "    latest_records = list(\n"
      + "        butler.registry.queryDimensionRecords(dimension, **query_kwargs).order_by('-day_obs').limit(1)\n"
      + "    )\n"
      + "    if latest_records:\n"
      + "        query_kwargs['where'] = f\"day_obs={int(latest_records[0].day_obs)}\"\n\n"
      + "records = butler.registry.queryDimensionRecords(dimension, **query_kwargs).order_by(\n"
      + "    *normalize_order_by(dataset_type, order_by, reverse)\n"
      + ")\n"
      + "if offset > 0:\n"
      + "    records = islice(records, offset, offset + limit)\n"
      + "else:\n"
      + "    records = records.limit(limit)\n\n"
      + "for record in records:\n"
      + "    print(record)",
    )
  })
})
