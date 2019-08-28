#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
	long_description = fh.read()

setuptools.setup(
    name="StatsBot",
    version="0.1",
    author="MakoEdits",
    author_email="makoegfx@gmail.com",
    description="Twitch bot for displaying Rainbow Six Siege stats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MakoEdits/StatsBot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)