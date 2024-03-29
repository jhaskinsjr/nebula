# Amanatsu Pipeline Overview

The Amanatsu implementation is actually not a pipeline at all. Rather, it
merely fetches and executes instructions as rapidly as possible, updating
the register file and main memory as it does. Instead of spawning separate
processes for the register file and main memory, each is instantiated as
an object directly inside the main execution module
(see: [pipelines/amanatsu/implemnetation/fastcore.py](implementation/fastcore.py)).
On my laptop, a Lenovo ThinkBook with an Core i7-8565U and 32 GB of RAM,
running Ubuntu 22.04, Amanatsu executes at a rate of approximately
10,200 instructions/second.

Because of its speed, Amanatsu is ideally suited for capturing snapshots
that can be resumed by Amanatsu, or any of the other pipeline models.

## Capturing A Snapshot

To capture snapshots after 100, 300, 900, and 2,700 instructions' worth of
execution:

    cd  ${HOME}/src/nebula/pipelines/amanatsu/
    mkdir -p /tmp/amanatsu/sum
    python3 ../../launcher.py \
        --log /tmp/amanatsu/sum \
        --service ../../toolbox/stats.py:localhost:22:-1 \
        --config stats:output_filename:/tmp/amanatsu/sum/stats.json \
        mainmem:filename:/tmp/amanatsu/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --snapshots 100 300 900 2700 \
        -- \
        12345 \
        localhost.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 17 19 23 29

This will create a series of files:

* **/tmp/amanatsu/sum/mainmem.raw.000000000000100.snapshot**: execution state captured after 100 instructions
* **/tmp/amanatsu/sum/mainmem.raw.000000000000300.snapshot**: execution state captured after 300 instructions
* **/tmp/amanatsu/sum/mainmem.raw.000000000000900.snapshot**: execution state captured after 900 instructions
* **/tmp/amanatsu/sum/mainmem.raw.000000000002700.snapshot**: execution state captured after 2,700 instructions

## Restoring From A Snapshot

Any of the pipelines can restore state from a snapshot and resume execution,
e.g.:

    cd  ${HOME}/src/nebula/pipelines/pompia/
    python3 ../../launcher.py \
        --log /tmp/pompia/sum \
        --service ../../toolbox/stats.py:localhost:22:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --restore /tmp/amanatsu/sum/mainmem.raw.000000000000900.snapshot \
        -- \
        12345 \
        localhost.nebula

Note: (1) the `--restore` parameter is included; and (2) the command that
was executed to create the snapshots (`../../examples/bin/sum 2 3 5 7`...) is
omitted. In this example, the Pompia pipeline should return

    129

On my laptop, resuming from this snapshot, Pompia finishes executing in
a little more than 8 minutes, whereas executing the same command line
end-to-end requires more than 11 minutes.

### What Is An Amanatsu?

See: https://en.wikipedia.org/wiki/Amanatsu.