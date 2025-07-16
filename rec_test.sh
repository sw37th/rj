#!/bin/sh

_tt_start=$(date +"%H:%M" -d "2 minute"):00
_bs_start=$(date +"%H:%M" -d "3 minute"):00

#_rectime="00:01:00"
_rectime=""  # default 00:29:30

./rj add 22 test_tbs   today ${_tt_start} ${_rectime}
./rj add 25 test_ntv   today ${_tt_start} ${_rectime}
./rj add 26 test_nhke  today ${_tt_start} ${_rectime}
./rj add 27 test_nhkg  today ${_tt_start} ${_rectime}

./rj add 101 test_nhkbs  today ${_bs_start} ${_rectime}
./rj add 161 test_bstbs  today ${_bs_start} ${_rectime}
./rj add 211 test_bs11   today ${_bs_start} ${_rectime}
./rj add 222 test_twelve today ${_bs_start} ${_rectime}
