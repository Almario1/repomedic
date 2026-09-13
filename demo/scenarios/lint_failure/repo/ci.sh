#!/bin/sh
python3 lint.py src.py && python3 -m unittest discover -s . -p "test_*.py" -t .
