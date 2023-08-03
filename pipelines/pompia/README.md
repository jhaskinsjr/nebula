# Pompia Pipeline Overview

The Pompia implementation uses a six-stage design that is similar to the
Oroblanco pipeline. It features an L1 instruction cache, an L1 data cache,
and a unified L2 cache, but omits branch prediction. Also different:
instruction fetch is performed on a per-cache-block basis, multiple
instructions can be decoded per cycle, and only a single LOAD/STORE
instruction is allowed in-flight at a time (to allow a greatly simplified
load-store unit design). Pompia allows multiple instructions to issue per
cycle, in-order, so long as there is no read-after-write hazard. This
design is a bit simpler than Oroblanco.

### What Is An Pompia?

See: https://en.wikipedia.org/wiki/Pompia.