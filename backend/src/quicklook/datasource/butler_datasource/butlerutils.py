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