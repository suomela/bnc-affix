#!/bin/bash

types=../../types
export PYTHONPATH=../lib

rm -rf output-bnc output-morphoquantics plot tmp html db
bin/process-morphoquantics || exit 1
bin/process-bnc || exit 1
bin/create-db || exit 1
$types/bin/types-run --bindir=$types/bin --recalc --citer=100000 --piter=100000 || exit 1
$types/bin/types-plot --bindir=$types/bin --type-lists --sample-lists || exit 1
