#!/bin/bash

for d in er adverb; do
    (cd $d && ../lib/helper.sh "$@") || exit 1
done
