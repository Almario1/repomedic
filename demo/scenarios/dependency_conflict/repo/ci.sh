#!/bin/sh
PYTHONPATH=vendor python3 check_env.py && PYTHONPATH=vendor python3 -m unittest discover -s . -p "test_*.py" -t .
