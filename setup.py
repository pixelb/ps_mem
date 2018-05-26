# -*- coding: utf-8 -*-

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="ps_mem",
    version="3.12",
    author="Pádraig Brady",
    author_email="P@draigBrady.com",
    description=("A utility to report core memory usage per program"),
    license="LGPLv2",
    keywords="memory RAM profile program linux",
    url="http://github.com/pixelb/ps_mem",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Programming Language :: Python",
    ],
    py_modules = ['ps_mem'],
    entry_points={'console_scripts':['ps_mem = ps_mem:main']}
)
