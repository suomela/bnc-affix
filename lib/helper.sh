#!/bin/bash

rm -rf output/*

export PYTHONPATH=../lib
bin/process-morphoquantics || exit 1
bin/process-bnc || exit 1
bin/create-db || exit 1

types="$(pwd)/../../types"

cd output || exit 1
if [ "$1" = "--quick" ]; then
    $types/bin/types-run --bindir=$types/bin --recalc --citer=100000 --piter=100000 || exit 1
else
    $types/bin/types-run --bindir=$types/bin --recalc --piter=10000000 || exit 1
fi
$types/bin/types-plot --bindir=$types/bin --type-lists --sample-lists || exit 1
$types/bin/types-plot --bindir=$types/bin --type-lists --sample-lists --slides --htmldir=html-slides --plotdir=plot-slides || exit 1
