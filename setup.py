import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "aglais_benchmark",
    version = "0.2.6",
    author = "Stelios Voutsinas",
    author_email = "stv@roe.ac.uk",
    description = ("A testing suite for Aglais"),
    license = "BSD",
    keywords = "aglais_benchmark",
    url = "https://github.com/wfau/aglais-testing",
    include_package_data = True,
    packages=['aglais_benchmark'],
    long_description="README",
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: Free For Home Use",
        "Programming Language :: Python"
    ],
    install_requires=[
        'zdairi @ git+https://github.com/stvoutsin/zdairi',
        'simplejson'
    ]
)

