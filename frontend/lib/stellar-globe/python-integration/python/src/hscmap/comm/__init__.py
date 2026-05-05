import json
import os
from typing import Any, Dict, Optional

from hscmap.models.Open import Model as Open

from .base import CommBase


def new_comm(open_msg: Open, options: Optional[Any]) -> CommBase:
    if options is None:  # pragma: no cover
        options = default_options()
    if options.__class__.__name__ == 'JupyterLabCommOptions':
        from .jupyterlab import JupyterLabComm

        return JupyterLabComm(open_msg, options)  # type: ignore # pragma: no cover
    elif options.__class__.__name__ == 'HscmapServerCommOptions':  # pragma: no cover
        from .hscmapserver import HscmapServerComm

        return HscmapServerComm(open_msg, options)  # type: ignore
    elif options.__class__.__name__ == 'MockCommOptions':
        from .mock import MockComm

        return MockComm(open_msg, options)  # type: ignore
    else:  # pragma: no cover
        raise ValueError(f'Unknown comm type: {type}')


def default_options():  # pragma: no cover
    env_prefix = 'stellar_globe_comm_'
    type = os.environ.get(f'{env_prefix}type', 'jupyterlab')
    if type == 'jupyterlab':
        from .jupyterlab import JupyterLabCommOptions

        return JupyterLabCommOptions()
    elif type == 'hscmapserver':
        from .hscmapserver import HscmapServerCommOptions

        return HscmapServerCommOptions(
            backend_url=os.environ.get(f'{env_prefix}backend_url', 'http://localhost:8000'),
            frontend_url=os.environ.get(f'{env_prefix}frontend_url', 'http://localhost:5173'),
        )
    elif type == 'mock':
        from .mock import MockCommOptions

        return MockCommOptions(
            base_url=os.environ.get(f'{env_prefix}base_url', 'http://localhost:8000'),
        )
    else:
        raise ValueError(f'Unknown comm type: {type}')
