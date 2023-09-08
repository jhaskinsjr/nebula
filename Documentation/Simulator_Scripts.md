# Simulator Scripts

The simulator executes according to instructions in an execute script.
Consider the script pipelines/pompia/init.nebula:

    # Sample μService-SIMulator script
    # NOTE: Nebula's multicore support can execute across multiple machines!
    # core 0
    service implementation/regfile.py:localhost:0
    service implementation/fetch.py:localhost:0
    service implementation/decode.py:localhost:0
    service implementation/alu.py:localhost:0
    service implementation/lsu.py:localhost:0
    service implementation/commit.py:localhost:0
    service implementation/l2.py:localhost:0
    ## core 1
    #service implementation/regfile.py:localhost:1
    #service implementation/fetch.py:localhost:1
    #service implementation/decode.py:localhost:1
    #service implementation/alu.py:localhost:1
    #service implementation/lsu.py:localhost:1
    #service implementation/commit.py:localhost:1
    #service implementation/l2.py:localhost:1
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

The script is comprised of commands

    config A B C                    change configuration of service A field B to value C
    cycle                           print the cycle count to stdout
    register set A B                set register A to value B
    run                             begin execution
    service A:B:C                   stage service A on machine B as a part of core C
    spawn                           execute all staged services
    state                           print launcher's state (i.e., variables, etc) to stdout
    shutdown                        send shutdown signal to services, exit launcher