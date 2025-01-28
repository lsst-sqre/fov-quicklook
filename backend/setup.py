from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).parent

setup(
    name='quicklook',
    version='0.1.0',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    python_requires='>=3.13',
    install_requires=[
        'pydantic-settings',
        'fastapi',
        'uvicorn',
        'uvicorn[standard]',
        'minio',
        'astropy',
        'rtree',
        'zstandard',
        'aiohttp',
        'SQLAlchemy==2.*',
        'alembic==1.12.*',
        'tqdm',
        'lsst-daf-butler',
        'boto3',
        'psycopg2-binary',
    ],
    extras_require={
        'dev': [
            'httpx',
            'pdbpp',
            'requests',
            'pytest-watch',
            'pytest-cov',
            'pytest-env',
            'pytest-asyncio',
            'pytest-watch',
            'black',
        ],
    },
)
