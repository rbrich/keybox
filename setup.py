#!/usr/bin/env python3

from setuptools import setup

setup(
    name='pwlockr',
    version='0.1',
    description='Storage for passwords, encrypted with GPG',
    author='Radek Brich',
    author_email='radek.brich@devl.cz',
    license='MIT',
    url='https://github.com/rbrich/pwlockr',
    packages=['pwlockr'],
    entry_points={
        'console_scripts': [
            'pw = pwlockr.main:main',
        ],
    },
)
