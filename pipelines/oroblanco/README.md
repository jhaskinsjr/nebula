# Oroblanco Pipeline Overview

The Oroblanco implementation uses a six-stage design that is similar to the
Lime pipeline. In addition to an L1 instruction cache, an L1 data cache,
and a unified L2 cache, Oroblanco also freatures result forwarding, and
branch prediction and branch target
buffering. Whenever a new taken branch is encountered, an entry is created for
it in the branch target buffer (BTB). In subsequent executions, if a branch
is taken its counter is incremented (saturating at 3) and the target
instructions are buffered into the BTB entry; if a branch is not taken its
counter is decremented; when a branch's counter reaches 0, it is evicted from
the BTB since it is occupying space that could be used by a branch that would
benefit from the BTB.

The branch target buffer functionality is implemented in the
`SimpleBTB` module (see: components/simplebtb/), which supports the
least-recently used and random replacement policies.

### What Is An Oroblanco?

See: https://en.wikipedia.org/wiki/Oroblanco.