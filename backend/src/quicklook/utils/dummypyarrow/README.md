# DummyPyarrow

`lsst.daf.butler` depends on `pyarrow`. `pyarrow` requires x86_v2, which does not work in some environments.
In `fov-quicklook`, the `pyarrow` functionality within `butler` is not used, so we replace `pyarrow` with a dummy that does not depend on x86_v2, allowing `butler` to run.
