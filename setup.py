#!/usr/bin/env python3

from setuptools import setup
from pathlib import Path

try:
    from Cython.Build import cythonize
except ImportError:
    def cythonize(*_args):
        return []

setup_dir = Path(__file__).parent

setup(
    name='keybox',
    version=(setup_dir / 'VERSION').read_text().strip(),
    description='Simple password manager. Stores secrets in encrypted tab-delimited table.',
    long_description=(setup_dir / "README.rst").read_text(),
    long_description_content_type='text/x-rst',
    author='Radek Brich',
    author_email='radek.brich@devl.cz',
    license='MIT',
    url='https://github.com/rbrich/keybox',
    packages=['keybox', 'keybox.backend'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'keybox = keybox.main:main',
        ],
    },
    ext_modules=cythonize('cryptoref/cryptoref.pyx'),
    setup_requires=['pytest-runner', 'Cython'],
    install_requires=['pynacl', 'prompt_toolkit', 'blessed', 'pyperclip'],
    tests_require=['pytest', 'argon2-cffi'],
)
