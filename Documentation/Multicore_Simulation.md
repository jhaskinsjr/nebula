# Multicore Simulations

Nebula also supports multicore simulations, and can place the services for
each core on a single machine, and accommodate multiple cores spanning
multiple machines. Consider the following distributed.nebula file:

    # Sample multicore Nebula script
    # core 0; not run on localhost
    service implementation/regfile.py:picard.local:22:0:0
    service implementation/fetch.py:picard.local:22:0:0
    service implementation/decode.py:picard.local:22:0:0
    service implementation/alu.py:picard.local:22:0:0
    service implementation/lsu.py:picard.local:22:0:0
    service implementation/commit.py:picard.local:22:0:0:"--cores 0-0 --next mem"
    service implementation/l2.py:picard.local:22:0:0
    # core 1; not run on localhost
    service implementation/regfile.py:riker.local:22:1:1
    service implementation/fetch.py:riker.local:22:1:1
    service implementation/decode.py:riker.local:22:1:1
    service implementation/alu.py:riker.local:22:1:1
    service implementation/lsu.py:riker.local:22:1:1
    service implementation/commit.py:riker.local:22:1:1:"--cores 1-1 --next mem"
    service implementation/l2.py:riker.local:22:1:1
    spawn
    config mainmem:peek_latency_in_cycles 25
    config fetch:l1ic_nsets 16
    config fetch:l1ic_nways 2
    config fetch:l1ic_nbytesperblock 16
    config fetch:l1ic_evictionpolicy lru # random
    config decode:max_instructions_to_decode 4
    config l2:nsets 32
    config l2:nways 16
    config l2:nbytesperblock 16
    config l2:evictionpolicy lru # random
    config l2:hitlatency 5
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
        --service ../../toolbox/stats.py:localhost:22:-1:-1 ../../components/simplemainmem/mainmem.py:localhost:22:-1:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        distributed.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 , ../../examples/bin/sort 7 2 3 5

where each binary-parameter set is separated by a comma.

As the binaries execute, a rudimentary MMU (see: [components/simplemmu/](../components/simplemmu/__init__.py)) will
map addresses from core 0 to separate addresses from core 1 so that the two
simulations can proceed concurrently without clobbering one another's state.

### Heterogeneous Cores

In addition to supporting multicore simulations distributed across
multiple, different nodes, Nebula also supports simulations with different
cores. Consider, for instance, [chips/4t4b/localhost.nebula](../chips/4t4b/localhost.nebula),
which describes a processor with 4 [Tangelo](../pipelines/tangelo/README.md) cores
and 4 [Bergamot](../pipelines/bergamot/README.md) cores.

```
# Sample Nebula script
# performance cores (Tangelo)
service ../../pipelines/tangelo/implementation/regfile.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/brpred.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/fetch.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/decode.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/issue.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/alu.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/lsu.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/commit.py:localhost:22:0:3
service ../../pipelines/tangelo/implementation/l2.py:localhost:22:-1:-1:"--cores 0-1 --next l3"
service ../../pipelines/tangelo/implementation/l2.py:localhost:22:-1:-1:"--cores 2-3 --next l3"
service ../../pipelines/tangelo/implementation/l3.py:localhost:22:-1:-1:"--cores 0-3 --next mem"
service ../../pipelines/tangelo/implementation/watchdog.py:localhost:22:0:3
# efficiency cores (Bergamot)
service ../../pipelines/bergamot/implementation/simplecore.py:localhost:22:4:7
service ../../pipelines/bergamot/implementation/regfile.py:localhost:22:4:7
service ../../pipelines/bergamot/implementation/decode.py:localhost:22:4:7
service ../../pipelines/bergamot/implementation/execute.py:localhost:22:4:7
service ../../pipelines/bergamot/implementation/watchdog.py:localhost:22:4:7
spawn
config brpred:btac_entries 32
config brpred:predictor_type bimodal
config brpred:predictor_entries 32
config fetch:l1ic_nsets 32
config fetch:l1ic_nways 1
config fetch:l1ic_nbytesperblock 16
config fetch:l1ic_evictionpolicy lru # random
config decode:max_bytes_to_decode 16
config alu:result_forwarding True
config lsu:l1dc_nsets 16
config lsu:l1dc_nways 2
config lsu:l1dc_nbytesperblock 16
config lsu:l1dc_evictionpolicy lru # random
config l2:nsets 16
config l2:nways 8
config l2:nbytesperblock 16
config l2:evictionpolicy lru # random
config l2:hitlatency 5
config l3:nsets 64
config l3:nways 8
config l3:nbytesperblock 32
config l3:evictionpolicy lru # random
config l3:hitlatency 25
config watchdog:result_name retire
config watchdog:result_cycles 10000
run
shutdown
```

Among the four Tangelo cores, there are two unified L2 caches that are
shared by two cores apiece, and a unified L3 cache that is shared by all
four cores. The much less sophisticated Bergamot cores communicate
directly... and very slowly... with main memory.