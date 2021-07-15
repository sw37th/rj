#!/bin/bash
#_opt="-v"
_opt=""
python3 -m unittest ${_opt} tests/test_openpbs.py
python3 -m unittest ${_opt} tests/test_cliutil.py
python3 -m unittest ${_opt} tests/test_init.py
