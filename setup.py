#!/usr/bin/env python3

from setuptools import setup

setup(
    name='keys',
    version='0.1',
    description='Storage for passwords, encrypted with GPG',
    author='Radek Brich',
    author_email='radek.brich@devl.cz',
    license='MIT',
    url='https://github.com/rbrich/keys',
    packages=['keys'],
    entry_points={
        'console_scripts': [
            'pw = keys.main:main',
        ],
    },
)
