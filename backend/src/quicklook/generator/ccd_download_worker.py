from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from quicklook.datasource import get_datasource
from quicklook.types import CcdDataRef, CcdName, VisitName


def main() -> int:
    try:
        visit, ccd_name, outpath = sys.argv[1:4]
    except ValueError:
        print(json.dumps({"error_type": "ValueError", "error_message": "expected visit, ccd_name, outpath"}))
        return 2

    ref = CcdDataRef(visit=VisitName(visit), ccd=CcdName(ccd_name))
    try:
        data = get_datasource().get_data_sync(ref)
        bytes_written = Path(outpath).write_bytes(data)
    except Exception as e:
        print(
            json.dumps(
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback_text": traceback.format_exc(),
                }
            )
        )
        return 1

    print(json.dumps({"bytes_written": bytes_written}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
