from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize([
        "ip_operator/ip_scorer.pyx"
    ])
) 