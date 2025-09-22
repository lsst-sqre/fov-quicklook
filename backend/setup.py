from setuptools import setup, find_packages

setup(
    name='quicklook',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'pytest',
        'fastapi',
        'uvicorn',
        'aiohttp',
        'httpx',
        'requests',
        'sqlalchemy>=2.0',
        'pydantic-settings',
    ],
    extras_require={
        'dev': [
            'pytest-cov',
            'httpx',
            'requests',
            'pytest-asyncio',
        ],
    },
)
