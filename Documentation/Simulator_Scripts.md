# Simulator Scripts

The simulator executes according to instructions in an execute script.
Consider the script pipelines/pompia/localhost.nebula:

    # Sample Nebula script
    # NOTE: Nebula's multicore support can execute across multiple machines!
    # single-core
    service implementation/regfile.py:localhost:22:0:0
    service implementation/fetch.py:localhost:22:0:0
    service implementation/decode.py:localhost:22:0:0
    service implementation/alu.py:localhost:22:0:0
    service implementation/lsu.py:localhost:22:0:0
    service implementation/commit.py:localhost:22:0:0
    service implementation/l2.py:localhost:22:0:0
    ## quad-core
    #service implementation/regfile.py:localhost:22:0:3
    #service implementation/fetch.py:localhost:22:0:3
    #service implementation/decode.py:localhost:22:0:3
    #service implementation/alu.py:localhost:22:0:3
    #service implementation/lsu.py:localhost:22:0:3
    #service implementation/commit.py:localhost:22:0:3
    #service implementation/l2.py:localhost:22:0:3
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
    config mainmem:peek_latency_in_cycles 25
    config mainmem:filename /tmp/mainmem.raw
    config mainmem:capacity 4294967296
    config stats:output_filename /tmp/stats.json
    run
    shutdown

The script is comprised of commands:

    config A B C                    change configuration of service A field B to value C
    cycle                           print the cycle count to stdout
    register set A B                set register A to value B
    run                             begin execution
    service A:B:C:D:E               stage service A on machine B, connecting via SSH port C, as a part of cores D through E (where D:E = -1:-1 means visible to all cores)
    spawn                           execute all staged services
    state                           print launcher's state (i.e., variables, etc) to stdout
    shutdown                        send shutdown signal to services, exit launcher