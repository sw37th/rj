#!/bin/bash
python3 -m unittest -v tests/test_openpbs.py
python3 -m unittest -v tests/test_cliutil.py
python3 -m unittest -v tests/test_init.py
