#!/usr/bin/env python3

import sys
from setuptools import setup

if sys.version_info.major == 3 and sys.version_info.minor <= 2:
    # Require funcsigs for Python 3.2
    requires = ['funcsigs']
else:
    requires = []

setup(
    name='keybox-keys',
    version='0.1',
    description='Storage for passwords, encrypted with GPG',
    author='Radek Brich',
    author_email='radek.brich@devl.cz',
    license='MIT',
    url='https://github.com/rbrich/keys',
    packages=['keys'],
    entry_points={
        'console_scripts': [
            'keys = keys.main:main',
        ],
    },
    setup_requires=['pytest-runner'],
    install_requires=requires,
    tests_require=['pytest', 'ptyprocess'],
)
