from setuptools import find_packages, setup

setup(
    name='hscmap',
    version='0.0.0',
    python_requires='>=3.8',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[],
    extras_require={
        'dev': [
            'pytest',
            'pytest-cov',
            'pytest-watch',
            'pandas',
            'numpy',
            'requests',
            'datamodel-code-generator==0.25.*',
            'build',
            'sphinx',
            'websockets',
        ],
        'hscmapserver': [
            'websockets',
        ],
    },
)
