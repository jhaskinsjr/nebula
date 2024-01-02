# Pompia Pipeline Overview

The Pompia implementation uses a seven-stage design that is similar to the
Oroblanco pipeline (**DEPRECATED**; tag: `v0.9.0`). It features an L1
instruction cache, an L1 data cache,
and a unified L2 cache, but omits branch prediction. Also different:
instruction fetch is performed on a per-cache-block basis, and multiple
instructions can be decoded per cycle. Pompia allows multiple instructions
to issue per cycle, in-order, so long as there is no read-after-write
hazard.

### What Is A Pompia?

See: https://en.wikipedia.org/wiki/Pompia.