#!/bin/sh
# Stand-in for the repo's CI test command.
python3 -m unittest discover -s . -p "test_*.py" -t .
