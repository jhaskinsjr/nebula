# Multicore Simulations

Nebula also supports multicore simulations, and can place the services for
each core on a single machine, and accommodate multiple cores spanning
multiple machines. Consider the following distributed.nebula file:

    # Sample multicore Nebula script
    # core 0
    service implementation/regfile.py:picard.local:22:0:0   # not run on localhost!
    service implementation/fetch.py:picard.local:22:0:0     # not run on localhost!
    service implementation/decode.py:picard.local:22:0:0    # not run on localhost!
    service implementation/alu.py:picard.local:22:0:0       # not run on localhost!
    service implementation/lsu.py:picard.local:22:0:0       # not run on localhost!
    service implementation/commit.py:picard.local:22:0:0    # not run on localhost!
    service implementation/l2.py:picard.local:22:0:0        # not run on localhost!
    # core 1
    service implementation/regfile.py:riker.local:22:1:1    # not run on localhost!
    service implementation/fetch.py:riker.local:22:1:!      # not run on localhost!
    service implementation/decode.py:riker.local:22:1:!     # not run on localhost!
    service implementation/alu.py:riker.local:22:1:1        # not run on localhost!
    service implementation/lsu.py:riker.local:22:1:!        # not run on localhost!
    service implementation/commit.py:riker.local:22:1:!     # not run on localhost!
    service implementation/l2.py:riker.local:22:1:1         # not run on localhost!
    spawn
    config mainmem:peek_latency_in_cycles 25
    config fetch:l1ic_nsets 16
    config fetch:l1ic_nways 2
    config fetch:l1ic_nbytesperblock 16
    config fetch:l1ic_evictionpolicy lru # random
    config decode:max_instructions_to_decode 4
    config l2:l2_nsets 32
    config l2:l2_nways 16
    config l2:l2_nbytesperblock 16
    config l2:l2_evictionpolicy lru # random
    config l2:l2_hitlatency 5
    config stats:output_filename /tmp/stats.json
    run
    shutdown

All the services for core 0 are executed on the server picard.local,
and all the services for core 1 are executed on the server riker.local.
Both cores are Pompia cores, and both are identically configured. Both
will commence execution when the distributed.nebula "run" command is
executed by the launcher.

To execute across N cores, it is necessary to supply N binaries and their
parameters, e.g.:

    python3 ../../launcher.py \
        --log /tmp/pompia/sum \
        --service ../../toolbox/stats.py:localhost:22:-1:-1 implementation/mainmem.py:localhost:22:-1:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        distributed.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 , ../../examples/bin/sort 7 2 3 5

where each binary-parameter set is separated by a comma.

As the binaries execute, a rudimentary MMU (see: components/simplemmu/) will
map addresses from core 0 to separate addresses from core 1 so that the two
simulations can proceed concurrently without clobbering one another's state.