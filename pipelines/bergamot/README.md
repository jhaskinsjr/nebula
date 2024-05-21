# Bergamot Pipeilne Overview

The Bergamot pipeilne implementation uses a very simple design wherein only
one stage operates per cycle. The core
(see: pipelines/bergamot/implementation/simplecore.py) orchestrates all
operations in the execution of each instruction; to wit:

1. fetch PC from the register file (see: pipelines/bergamot/implementation/regfile.py)
2. fetch instruction bytes from main memory (see: components/simplemainmem/mainmem.py)
3. decode instruction from raw bytes (see: pipelines/bergamot/implementation/decode.py)
4. fetch source operands from register file
5. execute instruction (see: pipelines/bergamot/implementation/execute.py)
6. write back destination register
7. update PC

None of these operations overlap (meaning that this implementation, arguably,
does not model a proper _pipeline_). But this very simple design was
instrumental in the early stages of the toolkit development, when instruction
implementations were being coded and debugged.

### What Is A Bergamot?

See: https://en.wikipedia.org/wiki/Bergamot_orange.