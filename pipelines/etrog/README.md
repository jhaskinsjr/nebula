# Etrog Pipeilne Overview

The Etrog pipeline is a **much faster** reimplementation of the
[Bergamot](../bergamot/README.md) example pipeline, featuring a very simple
core
(see: [pipelines/etrog/implementation/simplecore.py](implementation/simplecore.py))
which orchestrates all the operations of each instruction's execution;
to wit:

1. fetch PC from the register file
2. fetch instruction bytes from main memory
3. decode instruction from raw bytes
4. fetch source operands from register file
5. execute instruction
6. write back destination register
7. update PC

As with the Bergamot implementation, none of these operations overlap
(meaning that the Etrog example, arguably, does not model a proper
_pipeline_).

However, unlike Bergamot, which spawns the core, decoder, register file,
and execute units, as well as the main memory inside their own individual
processes, Etrog only spawns two processes: one for the core, one for
main memory. The decoder, register file, and execute units are
instantiated as objects inside the core; and messages are passed between
these objects entirely inside the core. This significantly reduces the
amount of interprocess communication, which significantly improves
simulation speed.

On my development laptop, Etrog executed "examples/bin/sieve 20" at a
rate of 24,000 simulated cycles per real-world second. Compare this to
Bergamot, which executed the same benchmark at a rate of only 3,200
simulated cycles per real-world second.

### What Is A Etrog?

See: https://en.wikipedia.org/wiki/Etrog.