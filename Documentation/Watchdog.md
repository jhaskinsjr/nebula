# Watchdog Tool

The watchdog component (see: [toolbox/watchdog.py](../toolbox/watchdog.py))
allows you to monitor the conduct of results/events as the simulator executes
and to end the simulation if the watched-for result/event occurs. Suppose,
for instance, you were optimizing instruction throughput and wanted to know
if it ever occurred that 1,000 or more cycles elapse between consecutive
instruction retires in the Rangpur pipeline while executing the `sum`
example binary:

    mkdir -p /tmp/rangpur/sum
    cd ${HOME}/src/nebula/pipelines/rangpur/
    python3 ../../launcher.py \
        --log /tmp/rangpur/sum \
        --service ../../toolbox/stats.py:localhost:-1:-1 ../../components/simplemainmem/mainmem.py:localhost:-1:-1 \
        --config stats:output_filename:/tmp/rangpur/sum/stats.json \
        mainmem:filename:/tmp/rangpur/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        watchdog:result_name:retire \
        watchdog:result_cycles:1000 \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        localhost.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13

Notice the `watchdog:result_name` and `watchdog:result_cycles` parameters
passed to `--config`. The former sets the name of the `result` channel
occurrence to watch for; the latter sets the threshold of occurrences that
trigger the end of simulation.

Similarly, if you wanted the watchdog to end simulation if ever more than
1,000 cycles elapse between consecutive instruction commits on the Bergamot
pipeline:

    mkdir -p /tmp/bergamot/sum
    cd ${HOME}/src/nebula/pipelines/bergamot/
    python3 ../../launcher.py \
        --log /tmp/bergamot/sum \
        --service ../../toolbox/stats.py:localhost:-1:-1 ../../components/simplemainmem/mainmem.py:localhost:-1:-1 \
        --config stats:output_filename:/tmp/bergamot/sum/stats.json \
        mainmem:filename:/tmp/bergamot/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        watchdog:event_name:commit \
        watchdog:event_cycles:1000 \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        localhost.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13

Notice that `watchdog:event_name` and `watchdog:event_cycles` are used
(rather than `watchdog:result_name` and `watchdog:result_cycles`), since
finished instructions are signaled on the `event` channel in the Bergamot
pipeline model (rather than the `results` channel).