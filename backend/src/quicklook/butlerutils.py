import os
import shutil
import stat


def chown_pgpassfile():
    if pgfile := os.environ.get('PGPASSFILE'):
        dest = f'/tmp/.pgpass'
        if pgfile != dest:
            shutil.copyfile(pgfile, dest)
            os.chmod(dest, stat.S_IRUSR)
            os.environ['PGPASSFILE'] = dest
