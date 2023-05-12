# Amanatsu Pipeline Overview

The Amanatsu implementation is actually not a pipeline at all. Rather, it
merely fetches and executes instructions as rapidly as possible, updating
the register file and main memory as it does. Instead of spawning separate
processes for the register file and main memory, each is instantiated as
an object directly inside the main execution module
(see: pipelines/amanatsu/implemnetation/fastcore.py).

### What Is An Amanatsu?

See: https://en.wikipedia.org/wiki/Amanatsu.