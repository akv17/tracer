from setuptools import setup, find_packages

from tracer import __version__

setup(
    name='tracer',
    version=__version__,
    description='runtime tracing of function arguments / return values',
    author='akv17',
    author_email='artem@nlogic.ai',
    url='https://github.com/akv17/tracer',
    packages=find_packages(exclude=('tests',)),
    python_requires='>=3.6',
)
