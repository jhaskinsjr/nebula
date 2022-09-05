# Lime Pipeline Overview

The Lime implementation uses a six-stage design that is essentially identical
to the six-stage pipeline of Clementine, featuring automatic read-after-write
hazard and control-flow hazard detection and handling, with each stage
operating independently. The key distinguishing features of Lime are its L1
instruction cache, L1 data cache, and unified L2 cache.

During instruction fetch, the L1 instruction cache is probed. If
the requested address is present in the cache, those bytes are sent
to the decode stage; if not, a request for those bytes is made to the L2.
Bytes are fetched from the L2 at the granularity of the L1 instruction cache
block size; when they arrive from the L2, they are installed into the
L1 instruction cache,
and then sent to the decode stage. The L1 data cache and unified L2 cache
operate in essentially
the same manner, but additionally handle STORE instructions that
poke data into the caches, with write-through semantics.

The cache functionality is implemented in the `SimpleCache` module (see:
components/simplecache/), which supports the least-recently used and
random replacement policies.

### What Is A Lime?

See: https://en.wikipedia.org/wiki/Lime_(fruit).