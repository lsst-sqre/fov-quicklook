`https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/debug/` で generator などと同じ環境のJupyterにアクセスできる。

↓のコードを実行すると

## raw

```python
import os
import shutil
import stat
import tempfile


def chown_pgpassfile() -> None:
    """Copy PGPASSFILE to a temporary location with appropriate permissions."""
    if pgfile := os.environ.get('PGPASSFILE'):
        # 一時ファイルを作成して確実に書き込めるようにする
        fd, temp_path = tempfile.mkstemp(prefix='.pgpass_')
        # mkstempが返すファイルディスクリプタを閉じる
        os.close(fd)

        # 内容をコピー
        shutil.copyfile(pgfile, temp_path)
        os.chmod(temp_path, stat.S_IRUSR)
        os.environ['PGPASSFILE'] = temp_path

chown_pgpassfile()

from lsst.daf.butler import Butler

default_instrument = 'LSSTCam'
butler = Butler("s3://embargo@rubin-summit-users/butler.yaml", instrument=default_instrument, collections=f"{default_instrument}/raw/all")  # type: ignore

data_type = 'raw'
refs = butler.query_datasets(data_type, where='detector=0', limit=100, order_by=['-day_obs', '-exposure'])

[r.dataId['exposure'] for r in refs]
```

## `post_isr_image`

```python
collection_lsstcam = collections = ['LSSTCam/runs/nightlyValidation']
butler_lsstcam = Butler("s3://embargo@rubin-summit-users/butler.yaml", collections=collection_lsstcam)
refs = butler_lsstcam.query_datasets('post_isr_image', where='detector=0', limit=100, order_by=['-day_obs', '-exposure'])
[r.dataId['exposure'] for r in refs]
```
