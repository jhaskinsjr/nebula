# Sample Pipelines

There have been many sample pipeline implementations, each named
after a citrus fruit. For a brief overview of each pipeline implmentation,
follow the links below:

* [Amanatsu](../pipelines/amanatsu/README.md)
* [Bergamot](../pipelines/bergamot/README.md)
* [Etrog](../pipelines/etrog/README.md)
* [Jabara](../pipelines/jabara/README.md)
* [Pompia](../pipelines/pompia/README.md)
* [Rangpur](../pipelines/rangpur/README.md)
* [Shangjuan](../pipelines/shangjuan/README.md)
* [Tangelo](../pipelines/tangelo/README.md)
* [Tangerine](../pipelines/tangerine/README.md)

Several... Clementine, Lime, and Oroblanco... are now deprecated. These
were very early efforts to forge Nebula pipeline examples, and have been
removed from the main branch of the Nebula source tree; they can be
located in the Git repo at tag `v0.9.0`, however.

The [Quick Start](../README.md#quick-start) guide shows how to execute
the examples/bin/sum program using the Pompia implementation; to use the
Amanatsu implementation, "cd" into the pipelines/amanatsu subdirectory
(instead of pipelines/pompia); to use the Bergamot implementation, "cd"
into the pipelines/bergamot subdirectory; etc.

With `executor.py` (see: [Large-Scale Studies](./Large-Scale_Studies.md)),
multiple pipelines can be easily be stress tested across a wide sweep of
different benchmarks (e.g., 3sat, sum, sieve, sort, negate, gzip) and
configurations (e.g., cache dimensions, branch predictor).

### Why citrus fruits?

Shortly after I began work on Nebula, I took a fierce interest in
citrus tree care and maintenance as I endeavored to grow lemons
and limes in [Zone 7](https://planthardiness.ars.usda.gov/).