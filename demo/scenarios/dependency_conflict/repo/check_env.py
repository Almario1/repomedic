"""Dependency gate: the app needs compatlib >= 2.0 behaviour."""

import sys

from compatlib import __version__


def parse(version):
    return tuple(int(part) for part in version.split("."))


if parse(__version__) < (2, 0):
    print(f"dependency version conflict: compatlib {__version__} < 2.0 required")
    sys.exit(1)
print("dependency check ok")
