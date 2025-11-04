from setuptools import setup, find_namespace_packages
from pathlib import Path

base_path = Path(__file__).parent

install_requires = [
    'pytest~=8.4.0',
    'fastapi~=0.117.0',
    'uvicorn~=0.36.0',
    'aiohttp~=3.12.0',
    'httpx~=0.28.0',
    'requests~=2.32.0',
    'sqlalchemy>=2.0.43',
    'pydantic-settings~=2.10.0',
    'numpy~=2.3.0',
    'astropy~=7.1.0',
    'boto3~=1.40.0',
    'minio~=7.2.0',
    'lsst-daf-butler',
    'psycopg2-binary',
    'zstandard',
    'websockets',
    'alembic',
    'asyncpg',
]

setup(
    name='quicklook',
    version='0.1.0',
    packages=find_namespace_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=install_requires,
    extras_require={
        'dev': [
            'pytest-cov~=7.0.0',
            'httpx~=0.28.0',
            'requests~=2.32.0',
            'pytest-asyncio~=1.2.0',
            'pytest-env~=1.1.0',
            'pytest-watch',
        ],
    },
)
