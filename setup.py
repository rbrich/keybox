#!/usr/bin/env python3

from setuptools import setup

setup(
    name='keybox',
    version='0.2',
    description='Storage for passwords, encrypted with GPG',
    author='Radek Brich',
    author_email='radek.brich@devl.cz',
    license='MIT',
    url='https://github.com/rbrich/keybox',
    packages=['keybox'],
    entry_points={
        'console_scripts': [
            'keybox = keybox.main:main',
        ],
    },
    setup_requires=['pytest-runner'],
    install_requires=['blessed'],
    tests_require=['pytest', 'pexpect'],
)
