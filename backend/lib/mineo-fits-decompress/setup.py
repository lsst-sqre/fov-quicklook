from setuptools import find_packages, setup, Extension
from pathlib import Path

module = Extension(
    'mineo_fits_decompress_c',
    libraries=['z'],
    extra_compile_args=['-DNDEBUG'],
    sources=[
        *[str(p) for p in Path('./fuse-fitsfs').glob('*.c')],
    ]
)

setup(
    name='mineo_fits_decompress',
    version='0.1.0',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    ext_modules=[module],
)
