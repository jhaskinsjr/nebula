# Rangpur Pipeline Overview

The Rangpur implementation uses an eight-stage design that is similar to the
Pompia pipeline. It features an L1 instruction cache, an L1 data cache,
a unified L2 cache, and branch prediction. As with Pompia, instruction fetch
is performed on a per-cache-block basis, multiple instructions can be
decoded per cycle, and multiple instructions can issue per cycle, in-order,
so long as there is no read-after-write hazard.

Unlike Pompia, however,
Rangpur features a decoupled fetcher: the branch predictor is in the first
stage of the pipeline, and drives the fetcher, which is in the second stage,
which supplies data to the decoder, etc. Branch predictions are communicated
from the branch predictor to the issue stage, which "stitches" predictions
onto their concommitant branches. When branches are correctly
predicted, execution continues unaffected; mispredicted branches are
signaled by the commit stage, allowing the branch predictor stage to
correct course.

### What Is A Rangpur?

See: https://en.wikipedia.org/wiki/Rangpur_(fruit).