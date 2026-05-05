```bash
Make dev
```

```python
from hscmap import Window
from hscmap.comm.hscmapserver import HscmapServerCommOptions

w = Window(comm_options=HscmapServerCommOptions(
    frontend_url="http://localhost:8000",
    backend_url="ws://localhost:8000",
    open_browser=True,
))
```
