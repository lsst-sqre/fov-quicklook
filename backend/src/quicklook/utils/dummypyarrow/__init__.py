from functools import cache
from quicklook.utils.cpuinfo import is_x86_v2
from pathlib import Path
import sys


def activate_dummy_pyarrow_when_non_x86_v2():
    if not is_x86_v2():
        pythonpath = Path(__file__).parent / 'pythonpath'
        if str(pythonpath) not in sys.path:
            sys.path.append(str(pythonpath))


activate_dummy_pyarrow_when_non_x86_v2()
