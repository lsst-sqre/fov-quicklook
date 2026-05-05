from setuptools import setup, find_packages

setup(
    name='hscmap-server',
    version='0.0.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        # List any dependencies your package requires
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-cov',
            'pytest-watch',
        ]
    },
)
