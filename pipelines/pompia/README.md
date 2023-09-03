# Pompia Pipeline Overview

The Pompia implementation uses a seven-stage design that is similar to the
Oroblanco pipeline. It features an L1 instruction cache, an L1 data cache,
and a unified L2 cache, but omits branch prediction. Also different:
instruction fetch is performed on a per-cache-block basis, and multiple
instructions can be decoded per cycle. Pompia allows multiple instructions
to issue per cycle, in-order, so long as there is no read-after-write
hazard. This design is a bit simpler than Oroblanco.

### What Is A Pompia?

See: https://en.wikipedia.org/wiki/Pompia.