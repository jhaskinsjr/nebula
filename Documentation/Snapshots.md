# Snapshots

The [Amanatsu](pipelines/amanatsu/README.md) and
[Jabara](pipelines/jabara/README.md) pipeline implementations do not
actually model pipelines. Rather, they merely execute instructions
as rapidly as possible. In addition to making them almost 100s of times
faster than any of the other sample pipelines (all of which, do model
execution in cycle-accurate detail), this makes Amanatsu and Jabara
ideally suited for capturing execution state in a snapshot that can be
resumed.

## Capturing A Set Of Snapshots

### Amanatsu

To capture snapshots at exactly 100, 300, 900, and 2,700 instructions' worth
of execution:

    cd  ${HOME}/src/nebula/pipelines/amanatsu/
    mkdir -p /tmp/amanatsu/sum
    python3 ../../launcher.py \
        --log /tmp/amanatsu/sum \
        --service ../../toolbox/stats.py:localhost:-1:-1 \
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

### Jabara

Jabara is almost 3 times faster than Amanatsu, but, because Jabara executes
entire basic blocks, it cannot guarantee that snapshots will be taken at
exactly the specified snapshot locations; consider:

    cd  ${HOME}/src/nebula/pipelines/jabara/
    mkdir -p /tmp/jabara/sum
    python3 ../../launcher.py \
        --log /tmp/jabara/sum \
        --service ../../toolbox/stats.py:localhost:22:-1:-1 \
        --config stats:output_filename:/tmp/jabara/sum/stats.json \
        mainmem:filename:/tmp/jabara/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --snapshots 100 300 900 2700 \
        -- \
        12345 \
        localhost.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 17 19 23 29

creates the files:

* **/tmp/jabara/sum/mainmem.raw.000000000000101.snapshot**: execution state captured at 101 instructions
* **/tmp/jabara/sum/mainmem.raw.000000000000301.snapshot**: execution state captured at 301 instructions
* **/tmp/jabara/sum/mainmem.raw.000000000000901.snapshot**: execution state captured at 901 instructions
* **/tmp/jabara/sum/mainmem.raw.000000000002702.snapshot**: execution state captured at 2,702 instructions

Notice that the snapshot instruction counts... 101, 301, 901, and 2702... are
not exactly equal to 100, 300, 900, and 2700. This is a very modest tradeoff
for the significant performance gain; but if snapshots must be exact, use
Amanatsu instead.

## Restoring From A Snapshot

Any of the pipelines can restore state from a snapshot and resume execution,
e.g.:

    cd  ${HOME}/src/nebula/pipelines/pompia/
    python3 ../../launcher.py \
        --log /tmp/pompia/sum \
        --service ../../toolbox/stats.py:localhost:-1:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --restore /tmp/amanatsu/sum/mainmem.raw.000000000000900.snapshot \
        -- \
        12345 \
        localhost.nebula

and

    cd  ${HOME}/src/nebula/pipelines/shangjuan/
    python3 ../../launcher.py \
        --log /tmp/shangjuan/sum \
        --service ../../toolbox/stats.py:localhost:22:-1:-1 \
        --config stats:output_filename:/tmp/shangjuan/sum/stats.json \
        mainmem:filename:/tmp/shangjuan/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --restore /tmp/jabara/sum/mainmem.raw.000000000000901.snapshot \
        -- \
        12345 \
        localhost.nebula

Note: (1) the `--restore` parameter is included; and (2) the command that
was executed to create the snapshots (`../../examples/bin/sum 2 3 5 7 11 13 17 19 23 29`...) is
omitted. In these examples, the [Pompia](../pipelines/pompia/README.md) and
[Shangjuan](../pipelines/shangjuan/README.md) pipelines should both return

    129