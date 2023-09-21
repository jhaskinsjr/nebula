# Sample Pipelines

At present, there are seven sample pipeline implementations: Amanatsu,
Bergamot, Clementine, Lime, Oroblanco, Pompia, and Rangpur.

The Quick Start section shows how to execute the examples/bin/sum program
using the Pompia implementation; to use the Amanatsu implementation, "cd"
into the pipelines/amanatsu subdirectory (instead of pipelines/pompia); to
use the Bergamot implementation, "cd" into the pipelines/bergamot subdirectory;
etc.

For a brief overview of each pipeline implmentation, follow the links below:

* [Amanatsu](../pipelines/amanatsu/README.md)
* [Bergamot](../pipelines/bergamot/README.md)
* [Clementine](../pipelines/clementine/README.md)
* [Lime](../pipelines/lime/README.md)
* [Oroblanco](../pipelines/oroblanco/README.md)
* [Pompia](../pipelines/pompia/README.md)
* [Rangpur](../pipelines/rangpur/README.md)
* [Shangjuan](../pipelines/shangjuan/README.md)

Please note that the Clementine, Lime, and Oroblanco pipelines were very
early efforts to forge Nebula pipeline examples. No longer under active
development, these three example pipelines are deprecated, but are kept in
this software tree, for now, as illucidative examples of how the Nebula
framework is used to construct cycle-accurate pipeline simulators.

More recently, sample pipelines are executed with `executor.py`
(see: [Large-Scale Studies](./Large-Scale_Studies.md)).
With `executor.py`, each pipeline can be easily be regression tested across
a wide sweep of different benchmarks (e.g., sum, sort, negate) and
configurations (e.g., L1 I-cache dimensions).