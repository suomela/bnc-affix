#!/bin/bash

for d in er; do
    (cd $d && ../lib/helper.sh "$@") || exit 1
done
