#!/bin/bash

rm -rf output/*

export PYTHONPATH=../lib
bin/process-morphoquantics || exit 1
bin/process-bnc || exit 1
bin/create-db || exit 1

types="$(pwd)/../../types"

cd output || exit 1
if [ "$1" = "--quick" ]; then
    $types/bin/types-run --recalc --citer=100000 --piter=100000 || exit 1
else
    $types/bin/types-run --recalc || exit 1
fi
$types/bin/types-web || exit 1
