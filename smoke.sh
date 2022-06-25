#!/bin/bash

N_CONCURRENT_SIMULATIONS=64

ROOT=/tmp/log
mkdir -p ${ROOT}

function do_bergamot {
    echo "Generating gold-standard outputs..."
    pushd pipelines/bergamot
    for bin in $( find ../../examples/bin/ -type f ) ; do
        BIN=$( basename ${bin} )
        LOGDIR=${ROOT}/gold/${BIN}
        if [[ ! -d ${LOGDIR} ]] ; then
            mkdir -p ${LOGDIR}
            (
                python3 ../../launcher.py -B \
                    --log ${LOGDIR} \
                    --mainmem /tmp/mainmem.$( uuid ).raw:$((2**32)) \
                    --config mainmem:peek_latency_in_cycles:1 \
                    -- \
                    $((10000+$((${RANDOM}%20000)))) main.ussim ${bin} 2 -3 -5 7 >${LOGDIR}/stdout.txt 2>${LOGDIR}/stderr.txt
            ) &
            sleep 1
        else
            echo "${LOGDIR} exists..."
        fi
    done
    popd

    echo "Waiting for gold-standard output generation to complete..."
    while [[ $( ps aux | egrep "python3.*log" | egrep -v grep | wc -l ) -gt 0 ]] ; do ( sleep 1) ; done
    echo "Done."
}

function do_lime {
    echo "Performing Lime tests..."
    pushd pipelines/lime
    for bin in $( find ../../examples/bin/ -type f ) ; do
        echo "${bin}"
        for s in 4 256 ; do
            for w in 1 4 ; do
                for n in 32 64 ; do
                    for x in 4 256 ; do
                        for y in 1 4 ; do
                            for z in 32 64 ; do
                                for a in 64 256; do
                                    for b in 1 8 ; do
                                        for c in 64 128 ; do
                                            for d in 1 5 ; do
                                                for l in 1 125 ; do
                                                    for t in 20 64 ; do
                                                        while [[ $( ps aux | egrep "python3.*launcher.py" | egrep -v "grep" | wc -l ) -ge ${N_CONCURRENT_SIMULATIONS} ]] ; do
                                                            sleep 1
                                                        done
                                                        PIPELINE=$( basename $( pwd ) )
                                                        BIN=$( basename ${bin} )
                                                        LOGDIR=${ROOT}/pipelines/${PIPELINE}/${BIN}/${s}/${w}/${n}/${x}/${y}/${z}/${a}/${b}/${c}/${d}/${l}/${t}
                                                        if [[ -d ${LOGDIR} ]] ; then continue ; fi
                                                        mkdir -p ${LOGDIR}
                                                        rm -rf ${LOGDIR}/*
                                                        (
                                                            python3 ../../launcher.py -B \
                                                                --log ${LOGDIR} \
                                                                --mainmem ${LOGDIR}/mainmem.raw:$((2**32)) \
                                                                --config \
                                                                    lsu:l1dc.nsets:${s} lsu:l1dc.nways:${w} lsu:l1dc.nbytesperblock:${n} \
                                                                    fetch:l1ic.nsets:${x} fetch:l1ic.nways:${y} fetch:l1ic.nbytesperblock:${z} \
                                                                    l2:l2.nsets:${a} l2:l2.nways:${b} l2:l2.nbytesperblock:${c} l2:l2.hitlatency:${d} \
                                                                    mainmem:peek_latency_in_cycles:${l} \
                                                                    decode:buffer_capacity:${t} \
                                                                    stats:output_filename:${LOGDIR}/stats.json \
                                                                -- \
                                                                $((10000+$((${RANDOM}%20000)))) main.ussim ${bin} 2 -3 -5 7 >${LOGDIR}/stdout.txt 2>${LOGDIR}/stderr.txt
                                                        ) &
                                                        sleep 1
                                                    done
                                                done
                                            done
                                        done
                                    done
                                done
                            done
                        done
                    done
                done
            done
        done
    done
    popd

    while [[ $( ps aux | egrep "python3.*log" | egrep -v grep | wc -l ) -gt 0 ]] ; do ( sleep 1) ; done
    echo "Done."
}

function verify_lime {
    echo "Verifying Lime test outputs..."
    for bin in $( find examples/bin/ -type f | egrep test ) ; do
        BIN=$( basename ${bin} )
        LOGDIR=${ROOT}/pipelines/lime/${BIN}
        N_RESULTS=$( find ${LOGDIR}/ -type f -name "regfile.py.log" -exec grep "register 10" {} \; | sort | uniq | wc -l )
        if [[ ${N_RESULTS} -ne 1 ]] ; then
            echo "${BIN} failed: Should be only 1 'register 10' output."
            exit 1
        fi
        GOLD_RESULT=$( egrep "register 10" ${ROOT}/gold/${BIN}/regfile.py.log | md5sum - | awk '{ print $1 }' )
        TEST_RESULT=$( egrep "register 10" $( find ${LOGDIR}/ -type f -name "regfile.py.log" | head -1 ) | md5sum - | awk '{ print $1 }' )
        if [[ ${GOLD_RESULT} != ${TEST_RESULT} ]] ; then
            echo "${BIN} failed: Gold result does not match test result."
            exit 2
        fi
    done
    echo "Success!"
    echo "Done."
}

function do_clementine {
    echo "Performing Clementine tests..."
    pushd pipelines/clementine
    for bin in $( find ../../examples/bin/ -type f ) ; do
        echo "${bin}"
        for l in 1 125 ; do
            for t in 20 64 ; do
                while [[ $( ps aux | egrep "python3.*launcher.py" | egrep -v "grep" | wc -l ) -ge ${N_CONCURRENT_SIMULATIONS} ]] ; do
                    sleep 1
                done
                PIPELINE=$( basename $( pwd ) )
                BIN=$( basename ${bin} )
                LOGDIR=${ROOT}/pipelines/${PIPELINE}/${BIN}/${l}/${t}
                if [[ -d ${LOGDIR} ]] ; then continue ; fi
                mkdir -p ${LOGDIR}
                rm -rf ${LOGDIR}/*
                (
                    python3 ../../launcher.py -B \
                        --log ${LOGDIR} \
                        --mainmem ${LOGDIR}/mainmem.raw:$((2**32)) \
                        --config \
                            mainmem:peek_latency_in_cycles:${l} \
                            decode:buffer_capacity:${t} \
                            stats:output_filename:${LOGDIR}/stats.json \
                        -- \
                        $((10000+$((${RANDOM}%20000)))) main.ussim ${bin} 2 -3 -5 7 >${LOGDIR}/stdout.txt 2>${LOGDIR}/stderr.txt
                ) &
                sleep 1
            done
        done
    done
    popd

    while [[ $( ps aux | egrep "python3.*log" | egrep -v grep | wc -l ) -gt 0 ]] ; do ( sleep 1) ; done
    echo "Done."
}

function verify_clementine {
    echo "Verifying Clementine test outputs..."
    for bin in $( find examples/bin/ -type f | egrep test ) ; do
        BIN=$( basename ${bin} )
        LOGDIR=${ROOT}/pipelines/clementine/${BIN}
        N_RESULTS=$( find ${LOGDIR}/ -type f -name "regfile.py.log" -exec grep "register 10" {} \; | sort | uniq | wc -l )
        if [[ ${N_RESULTS} -ne 1 ]] ; then
            echo "${BIN} failed: Should be only 1 'register 10' output."
            exit 1
        fi
        GOLD_RESULT=$( egrep "register 10" ${ROOT}/gold/${BIN}/regfile.py.log | md5sum - | awk '{ print $1 }' )
        TEST_RESULT=$( egrep "register 10" $( find ${LOGDIR}/ -type f -name "regfile.py.log" | head -1 ) | md5sum - | awk '{ print $1 }' )
        if [[ ${GOLD_RESULT} != ${TEST_RESULT} ]] ; then
            echo "${BIN} failed: Gold result does not match test result."
            exit 2
        fi
    done
    echo "Success!"
    echo "Done."
}

do_bergamot
do_clementine
verify_clementine
do_lime
verify_lime