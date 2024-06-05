# Tangelo Pipeline Overview

The Tangelo implementation is an evolution of Shangjuan. It uses
an eight-stage pipeline with a decoupled fetcher, features Gshare and
Bimodal branch prediction, a Branch Target Address Cache, an L1
instruction cache, L1 data cache, a unified L2 cache,
and branch prediction. Fetch is performed on a per-cache-block basis,
and multiple instructions can issue per cycle, in-order, until a
read-after-write hazard occurs, which blocks further issue until: (1)
the writing instruction's result is received through data forwarding;
(2) the writing instruction retires; or (3) the writing instruction is
flushed.

Unlike Shangjuan, an L2 cache can be shared by multiple cores.
Additionally Tangelo allows an optional L3 cache that can also be shared
by multiple cores' L2s. This shared caching feature is enabled by an
MMU that performs virtual-to-physical address translation *before*
L1 cache transactions which guarantees disambiguation amnog the various
cores inside the shared caches.

### What Is A Tangelo?

See: https://en.wikipedia.org/wiki/Tangelo.