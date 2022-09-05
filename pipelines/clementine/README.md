# Clementine Pipeline Overview

The Clementine implementation uses a six-stage design akin to the venerable
MIPS R3000, with automatic read-after-write hazard and control-flow hazard
detection and handling. Unlike Bergamot, there is no overarching core
controller. Rather, each stage operates more-or-less independently; to wit:

1. fetch instruction bytes from main memory (see: pipelines/clementine/implementation/fetch.py)
2. buffer and decode instruction bytes (see: pipelines/clementine/implementation/decode.py)
3. register access (see: pipelines/clementine/implementation/regfile.py)
4. execute arithmetic, logic, branch operation (see: pipelines/clementine/implementation/alu.py)
5. execute load/store operation (see: pipelines/clementine/implementation/lsu.py)
6. retire/flush instructions (see: pipelines/implementation/implementation/commit.py)

Read-after-write hazard detection is done in the decode stage, which halts
the consumer instruction until its concomitant producer instruction either
retires or is flushed by the commit
stage. Control-flow hazards are handled by the commit stage; when a
jump (JAL, JALR) or a taken branch (BEQ, BNE, BGE, BLT, BGEU, BLTU)
retires, the target PC is remembered and all
subsequent instructions will be flushed until the commit stage sees the
target instruction. Also, as soon as the jump/branch commits
the target PC is transmitted on the `results` channel where it is
sensed by the instruction fetch stage and the decode stage. The instruction
fetcher responds by beginning to fetch instruction bytes from the new PC;
the decoder responds by flushing all previously-decoded instructions.

### What Is A Clementine?

See: https://en.wikipedia.org/wiki/Clementine.