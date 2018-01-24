try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os.path
import re
VERSION_RE = re.compile(r'''__version__ = ['"]([-a-z0-9.]+)['"]''')
BASE_PATH = os.path.dirname(__file__)


with open(os.path.join(BASE_PATH, 'wsrpc', '__init__.py')) as f:
    try:
        version = VERSION_RE.search(f.read()).group(1)
    except IndexError:
        raise RuntimeError('Unable to determine version.')


setup(
    name='websocket-rpc',
    description='msgpack rpc over websocket',
    license='MIT',
    version=version,
    author='Yingbo Gu',
    author_email='tensiongyb@gmail.com',
    maintainer='Yingbo Gu',
    maintainer_email='tensiongyb@gmail.com',
    url='https://github.com/guyingbo/websocket-rpc',
    packages=['wsrpc'],
    python_requires='>=3.5',
    install_requires=[
        'websockets>=4.0.1',
        'msgpack>=0.5.1',
    ],
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
)
