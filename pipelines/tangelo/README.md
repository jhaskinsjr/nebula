# Tangelo Pipeline Overview

The Tangelo implementation is a mild evolution of Shangjuan. It uses
an eight-stage pipeline with a decoupled fetcher, features Gshare and
Bimodal branch prediction, a Branch Target Address Cache, an L1
instruction cache, L1 data cache, a unified L2 cache, and branch
prediction. Fetch is performed on a per-cache-block basis, and multiple
instructions can issue per cycle, in-order, until a read-after-write
hazard occurs, which blocks further issue until: (1) the writing
instruction's result is received through data forwarding; (2) the
writing instruction retires; or (3) the writing instruction is flushed.

Unlike Shangjuan, an L2 cache can be shared by multiple cores.
Additionally Tangelo allows an optional L3 cache that can also be shared
by multiple L2s. And this shared caching feature is supported by an
independent MMU so that virtual-to-physical address translation can
occur before accessing either the L1 data cache or L1 instruction cache.

### What Is A Tangelo?

See: https://en.wikipedia.org/wiki/Tangelo.