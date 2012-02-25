#!/usr/bin/python

import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "SmartRSSparser",
    author = "Adam Haney",
    version = "0.2.1",
    author_email = "adam.haney@retickr.com",
    description = ("A fascade for retickr that wraps around the Universal Feed Parser"),
    license = "Closed",
    keywords = "RSS",
    url = "http://about.retickr.com",
    packages=['smartrssparser'],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Framework",
        "License :: OSI Approved :: Closed",
    ],
    install_requires=[
        "BeautifulSoup"
        ]
)
