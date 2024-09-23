# Hyuganatsu Pipeline Overview

Hyuganatsu is a reimplementation of the
[Tangelo](../tangelo/README.md) pipeline model, but which places all of
the pipeline components... branch predictor, fetcher, decoder, issue,
ALU, LSU, and commit... inside a single process, rather than spread among
several processes. The L2, L3, and main memory all continue to exist
inside separate individual processes so that they many be shared among
multiple cores. (This is similar to the work done to create
[Etrog](../etrog/README.md), which is a reimplementation of
[Bergamot](../bergamot/README.md).)

### What Is A Hyuganatsu?

See: https://en.wikipedia.org/wiki/Hyuganatsu.