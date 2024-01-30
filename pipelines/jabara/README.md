# Jabara Pipeline Overview

The Jabara implementation is actually not a pipeline at all. Rather, like
[Amanatsu](../amanatsu/README.md), it merely fetches and executes
instructions as rapidly as possible. Unlike Amanatsu, which repeats a simple
fetch-decode-execute loop for each instruction, Jabara creates a cache of
basic blocks so that the fetch- and decode steps are only performed once
for each instruction;
see: [pipelines/jabara/implemnetation/basicblockcore.py](implementation/basicblockcore.py).
On my laptop, a Lenovo ThinkBook with an Core i7-8565U and 32 GB of RAM,
running Ubuntu 22.04, Jabara executes at a rate of approximately
24,000 instructions/second.

Because of its speed, Jabara is ideally suited for capturing snapshots
that can be resumed by Jabara, or any of the other pipeline models.

## Capturing A Snapshot

To capture snapshots after 100, 300, 900, and 2,700 instructions' worth of
execution:

    cd  ${HOME}/src/nebula/pipelines/jabara/
    mkdir -p /tmp/jabara/sum
    python3 ../../launcher.py \
        --log /tmp/jabara/sum \
        --service ../../toolbox/stats.py:localhost:22:-1 \
        --config stats:output_filename:/tmp/jabara/sum/stats.json \
        mainmem:filename:/tmp/jabara/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --snapshots 100 300 900 2700 \
        -- \
        12345 \
        localhost.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 17 19 23 29

This will create a series of files:

* **/tmp/jabara/sum/mainmem.raw.000000000000101.snapshot**: execution state captured at 101 instructions
* **/tmp/jabara/sum/mainmem.raw.000000000000301.snapshot**: execution state captured at 301 instructions
* **/tmp/jabara/sum/mainmem.raw.000000000000901.snapshot**: execution state captured at 901 instructions
* **/tmp/jabara/sum/mainmem.raw.000000000002702.snapshot**: execution state captured at 2,702 instructions

Notice that the snapshot instruction counts... 101, 301, 901, and 2702... are
not exactly equal to 100, 300, 900, and 2700. This is a byproduct of the fact
that Jabara executes whole basic blocks' worth of instructions. Since a basic
block did not end on exactly 100, 300, 900, or 2,700 instructions, Jabara was
forced to take the snapshot as soon as the instruction count was greater than
or equal to the snapshot specification (rather than just equal to).

If snapshots must be taken at precise instructions during execution, make
snapshots using [Amanatsu](../amanatsu/README.md), instead.

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
        --restore /tmp/jabara/sum/mainmem.raw.000000000000901.snapshot \
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

### What Is A Jabara?

See: https://en.wikipedia.org/wiki/Jabara_(citrus).