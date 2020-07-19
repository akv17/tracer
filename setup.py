from setuptools import setup, find_packages

from tracer import __version__

setup(
    name='tracer',
    version=__version__,
    description='runtime tracing of arguments / return values of callables',
    author='akv17',
    author_email='artem@nlogic.ai',
    url='https://github.com/akv17/tracer',
    packages=find_packages(exclude=('tests',)),
    python_requires='>=3.6',
)
