#!/usr/bin/env python3
"""
Setup script for Toggleman package
"""

from setuptools import setup, find_packages

setup(
    name="toggleman",
    version="1.0.0",
    author="Toggleman Team",
    description="Application toggle script manager for KDE Wayland",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.0",
        "pyyaml>=5.1.0",
        "dbus-python>=1.2.16",
    ],
    entry_points={
        "console_scripts": [
            "toggleman=toggleman.__main__:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Environment :: X11 Applications :: Qt",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
)