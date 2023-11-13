# Shangjuan Pipeline Overview

The Shangjuan implementation uses an eight-stage pipeline with a decoupled
fetcher like Rangpur. It features an L1 instruction cache, L1 data cache,
a unified L2 cache, and branch prediction. Fetch is
performed on a per-cache-block basis, and multiple instructions cahe issue
per cycle, in-order, until a read-after-write hazard occurs, which blocks
further issue until: (1) the writing instruction's result is received
through data forwarding; (2) the writing instruction retires; or (3) the
writing instruction is flushed.

Unlike Rangpur, which, for simplicity, imposed the restriction that only
a single LOAD instruction be in-flight at a time, Shangjuan allows any
mix of LOAD/STORE instructions in-flight concurrently, and the LSU
pipeline stage properly manages them. Also unlike Rangpur, Shangjuan
implements realistic, if very simple (Gshare, bimodal), branch prediction.
A branch is only ever predicted taken if the Branch Target Address Cache
has a target address associated with the predicted branch's address, and
the most significant bit of the counter associated with the branch is 1.

### Future Features

Shangjuan is a work in progress. Here are a few planned future features:

* value prediction
* return address stack

### What Is A Shangjuan?

See: https://en.wikipedia.org/wiki/Shangjuan.