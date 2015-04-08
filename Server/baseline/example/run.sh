#!/bin/bash

export LD_LIBRARY_PATH=./libs:${LD_LIBRARY_PATH}

FUZZID=`date "+%Y%m%d%H%M%S"`

echo "Fuzz ID: $FUZZID" >&2

if [ "$#" -eq 1 ]; then
        if [ "$1" == "-master" ]; then
                ./bin/afl-fuzz -i input -o output -M "$FUZZID" ./bin/instrumented_cmp
        else
                ./bin/afl-fuzz -i input -o output -S "$FUZZID" ./bin/instrumented_cmp
        fi
else
        ./bin/afl-fuzz -i input -o output -S "$FUZZID" ./bin/instrumented_cmp
fi