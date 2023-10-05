# Distributed Simulations

Because the Nebula framework spawns multiple independent
services that communicate over a TCP network, the services need not execute
on the same machine. This is what makes Nebula
**the world's first cloud-native microarchitecture simulation framework**!

Consider the following Pompia `.nebula` file (modified from localhost.nebula)
that spawns services on several different machines on my network:

    # Sample distributed Nebula script
    service implementation/regfile.py:picard.local:0   # not run on localhost!
    service implementation/fetch.py:riker.local:0      # not run on localhost!
    service implementation/decode.py:laforge.local:0   # not run on localhost!
    service implementation/alu.py:data.local:0         # not run on localhost!
    service implementation/lsu.py:worf.local:0         # not run on localhost!
    service implementation/commit.py:troi.local:0      # not run on localhost!
    service implementation/l2.py:crusher.local:0       # not run on localhost!
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

Recall that the mainmem.py and stats.py services are spawned locally using
the "--service" command line parameter.