# Welcome to μService-SIMulator!

The μService-SIMulator (ussim) is a framework for developing cyce-accurate
microprocessor simulators. At present, Python libraries for decoding and
executing one instruction set, RISC-V's RV64I, are included. (Most of the
RV64I instruction set is
implemented: both compressed and uncompressed versions of opcodes).
Additionally, this software package comes with four sample simulated
pipelines: Bergamot, Clementine, Lime, and Oroblanco.
Bergamot implements a very simple single-stage pipeline; Clementine
implements a slightly more sophisticated 6-stage pipeline
with automatic data- and control-hazard detection and handling; Lime
augments Clementine with an L1 instruction cache, L2 data cache, and a
unified L2 cache; and Oroblanco augments Lime with branch prediction and
branch target buffering.

## Software Architecture

### Philosophy: Simplicity And Flexibility Through Independence

The central design feature of ussim is an army of microservices...
independent processes running on the same machine (and soon, different
machines...
shouting out whatever they need, whatever information they wish to
communicate, whatever matters to them into the network where all other
microservices will receive it. If something shouted into the network
matters to one or more microservices, those microservices are free to act
upon it and, where appropriate, shout something back in response.

THIS IS AN INTENTIONAL DESIGN CHOICE!

While it would probably be faster to do point-to-point communication, where
microservices communicate directly to the microservice(s) that matter to
them, this architecture would require every microservice to have detailed
information about every other microservice. This rigidity is the antithesis
of the flexibility that software is supposed to facilitate.

There are no solutions, only tradeoffs. I have made this tradeoff knowingly,
willingly, intentionally, fully aware of the performance ramifications.
Notwithstanding this, I chose to trade away speed for flexibility.

The benefit of this design choice is the incredible simplicity of the
software that implements the pipeline logic. Since each step in the process
of executing an instruction (e.g., decode, register access, execute)
is handled by its own process, all the code for each step is
self-contained, making it easier to reason about.

Bergamot, for instance, is comprised of five Python files
(see: pipelines/bergamot/implementation/), four of which contain fewer than
150 lines of code. The lone standout is execute
(see: pipelines/bergamot/implementation/execute.py) which, despite handling
dozens of RISC-V
instructions, still occupies fewer than 700 lines of code.
Similarly, Clementine is comprised of seven Python files
(see: pipelines/clementine/implementation/),
all but one of which is less than 150 lines of code, with the ALU
logic (see: pipelines/clementine/implementation/alu.py)
still weighing in at under 400 lines of code.

These bite-sized units allow chunks of functionality to be cleanly
isolated from one another, making each easier to reason about, easier to
understand, and, as necessary for implementing novel design concepts,
easier to modify. Consider, for instance, that a change to a function
in the register file logic will almost certainly not alter functionality
implemented in the decoder logic; this reduces the amount of the system
that a developer has to be familiar with in order to be productive.

Furthermore, because the units communicate among themselves, it is easy
to construct a unit that monitors communications between the other
units to
count events (e.g., number of fetches, number of instructions flushed,
number of instructions retired).

### Communication Channels

There are two main communication channels that the microservices utilize:
`result` and `event`. The
former, as its name implies, is concerned with broadcasting output from the
various microservices, whereas the latter is concerned with broadcasing
requests for actions to be taken. To ask for the value stored in a register,
an `event` is sent, e.g.,

    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'get',
            'name': _insn.get('rs1'),
        }
    }})

To report the output of an operation, a `result` is sent, e.g.,

    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'flush': {
            'iid': _insn.get('iid'),
        },
    }})

One general-purpose rule of thumb is that incoming `result` messages should
be handled _before_ `event` messages, since `result` messages communicate
information that may be useful in processing `event` messages.

There are other channels as well; two highlights are the `info` channel, used
to echo debug or informational output, e.g., 

    service.tx({'info': '_insn : {}'.format(_insn)})

and the `shutdown` channel used to cleanly cease all ussim processes and
gracefully exit, e.g., 

    service.tx({'shutdown': None})

For a complete list, see the handler() function in launcher.py.

## Running

If you have not already done so, you will need to install pyelftools; see:

https://github.com/eliben/pyelftools

You will also need to set up passwordless SSH
access to your host machine; see:

https://www.ibm.com/support/pages/configuring-ssh-login-without-password

Once passwordless SSH has been set up, to quickly run, execute:

    cd pipelines/bergamot
    mkdir -p /tmp/bergamot/sum
    python3 ../../launcher.py \
        --log /tmp/bergamot/sum \
        --mainmem /tmp/bergamot/sum/mainmem.raw:$((2**32)) \
        --config stats:output_filename:/tmp/bergamot/sum/stats.json \
        --max_cycles 32000 \
        --snapshots 1000 \
        --break_on_undefined \
        -- \
        10000 \
        main.ussim \
        ../../examples/bin/sum 2 3 5 7 11 13

First, the "cd" command changes into the subdirectory with the
very simple, very primitive μService-SIMulator pipeline implementation
(codename: Bergamot).
Then, the "mkdir" command creates a directory into which each of
the service's log files will be deposited.
The "python3" command then executes the launcher
module (launcher.py). The launcher module will then begin by
opening a socket and accepting connections on port 10,000, executing
the script main.ussim, and
loading the binary "../../examples/bin/sum" together with its command-line
parameters "2 3 5 7 11 13", into the simulator's main memory; and simulating
for a maximum of 32,000 simulated cycles, taking snapshots (of the
simulated main memory and register file) every 1,000 simulated cycles, but
will cease execution if it encounters an instruction that is not (yet)
defined.

Once the simulation completes, the directory "/tmp/bergamot/sum" will
contain one log file for each of the services that executed during the
simulation, and a "stats.json" file, which contains statistics such as
number of simulated cycles, counts of the number of times each register
was fetched/written, counts of the number of committed instructions,
number of times each instruction type (e.g., ADD, ADDI, SD, SW) was decoded,
number of times each instruction type was executed, etc. The
JSON output file of more sophisticated implementations such as Oroblanco
contain additional statistics about caches and other elements of the
pipeline.

## Pipeline Designs

At present, there are four pipeline implementations: Bergamot, Clementine,
Lime, and Oroblanco.

The Running section above shows how to execute the examples/bin/sum program
using the Bergamot implementation; to use the Clementine implementation, "cd" into
the pipelines/clementine subdirectory (instead of pipelines/bergamot); to use the
Lime implementation, "cd" into the pipelines/lime subdirectory; to use the 
Oroblanco implementation, "cd" into the pipelines/oroblanco subdirectory.

### Bergamot

See: https://en.wikipedia.org/wiki/Bergamot_orange.

The Bergamot implementation uses a very simple design wherein only one stage
operates per cycle. The core (see: pipelines/bergamot/implementation/simplecore.py)
orchestrates all operations...

1. fetch PC from the register file (see: pipelines/bergamot/implementation/regfile.py)
2. fetch instruction bytes from main memory (see: pipelines/bergamot/implementation/mainmem.py)
3. decode instruction from raw bytes (see: pipelines/bergamot/implementation/decode.py)
4. fetch source operands from register file
5. execute instruction (see: pipelines/bergamot/implementation/execute.py)
6. write back destination register
7. update PC

None of these operations overlap (meaning that this implementation, arguably,
is not a pipeline). But this very simple design was instrumental in the early
stages of development, as instruction implementations were being coded and
debugged.

### Clementine

See: https://en.wikipedia.org/wiki/Clementine.

The Clementine implementation uses a six-stage design that operates in a
manner akin to the venerable MIPS R3000, with automatic read-after-write
hazard and control-flow hazard detection and handling. Unlike Bergamot, there
is no overarching control core. Rather, each stage operates more-or-less
independently...

1. fetch instruction bytes from main memory (see: pipelines/clementine/implementation/fetch.py)
2. buffer and decode instruction bytes (see: pipelines/clementine/implementation/decode.py)
3. register access (see: pipelines/clementine/implementation/regfile.py)
4. execute arithmetic, logic, branch operation (see: pipelines/clementine/implementation/alu.py)
5. execute load/store operation (see: pipelines/clementine/implementation/lsu.py)
6. retire/flush instructions (see: pipelines/implementation/implementation/commit.py)

Read-after-write hazard detection is done in the decode stage, which halts
the consumer instruction until the producer instruction either retires or is
flushed by the commit
stage. Control-flow hazards are handled by the commit stage when a
jump (JAL, JALR) or a taken branch (BEQ, BNE, BGE, BLT, BGEU, BLTU)
instruction retires; when this happens, the target PC is remembered and all
subsequent instructions will be flushed until the instruction at the target
PC arrives in the commit stage. Also, as soon at the jump/branch commits
the target PC is transmitted on the results channel where it is
sensed by the instruction fetch stage and the decode stage. The instruction
fetcher responds by beginning to fetch instruction bytes from the new PC;
the decoder responds by flushing all previously-decoded instructions.

### Lime

See: https://en.wikipedia.org/wiki/Lime_(fruit).

The Lime implementation uses a six-stage design that is essentially identical
to the six-stage pipeline of Clementine, featuring automatic read-after-write
hazard and control-flow hazard detection and handling, with each stage operating
independently. The key distinguishing features of Lime are its L1 instruction cache,
L1 data cache, and unified L2 cache.

During instruction fetch, the L1 instruction cache is probed
and if the requested address is present in the cache, those bytes are forwarded
to the decode stage; if not, a request for those bytes is made to the L2.
Bytes are fetched from the L2 at the granularity of the L1 instruction cache
block size; when they arrive from the L2, they are installed into the cache,
and then forwarded to the decode stage. The L1 data cache and unified L2 cache
operate in essentially
the same manner, but additionally handle STORE instructions that explicitly
poke data into the caches, with write-through semantics.

The cache functionality is implemented in the `SimpleCache` module (see:
components/simplecache/).

### Oroblanco

See: https://en.wikipedia.org/wiki/Oroblanco.

The Oroblanco implementation uses a six-stage design that is similar to the
Lime pipeline. In addition to an L1 instruction cache, an L1 data cache,
and a unified L2 cache, Oroblanco includes branch prediction and branch target
buffering. Whenever a new taken branch is encountered, an entry is created for
it in the branch target buffer (BTB). In subsequent executions, if a branch
is taken its counter is incremented (saturating at 3) and the target
instructions are buffered into the BTB entry; if a branch is not taken its
counter is decremented; when a branch's counter is 0, it is evicted from the
BTB since it is occupying space that could be used by a branch that would
benefit from the BTB.

The branch target buffer functionality is implemented in the
`SimpleBTB` module (see: components/simplebtb/).

## Simulator Scripts

The simulator executes according to instructions in an execute script.
Consider the script pipelines/lime/main.ussim:

    # Sample μService-SIMulator script
    service implementation/simplecore.py:localhost
    service implementation/regfile.py:localhost
    service implementation/mainmem.py:localhost
    service implementation/decode.py:localhost
    service implementation/execute.py:localhost
    spawn
    config mainmem peek_latency_in_cycles 5 # not super-realistic, but it makes the simulation end sooner
    config fetch l1ic.nsets 16
    config fetch l1ic.nways 1
    config fetch l1ic.nbytesperblock 8
    config decode buffer_capacity 32
    config lsu l1dc.nsets 32
    config lsu l1dc.nways 4
    config lsu l1dc.nbytesperblock 16
    cycle
    loadbin /tmp/mainmem.raw 0x80000000 0x40000000 main # using /tmp/mainmem.raw as the main memory file,
                                                        # set x2 to 0x80000000 and %pc to 0x40000000, then
                                                        # load binary (e.g., ../../examples/bin/sum), and
                                                        # execute beginning from the "main" symbol in the
                                                        # binary's .text section
    run
    cycle
    state
    shutdown

The script is comprised of commands

    config A B C                    change configuration of service A field B to value C
    cycle                           print the cycle count to stdout
    loadbin A B C D E X             set main memory file A; locate stack at address B; locate code
                                    at address C; and begin execution from .text section label D 
    restore A B                     restore previously captured state in B to main memory file A
    register set A B                set register A to value B
    run                             begin execution
    service A:B                     stage service A on machine B
    spawn                           execute all staged services
    state                           print launcher's state (i.e., variables, etc) to stdout
    shutdown                        send shutdown signal to services, exit launcher

The script pipelines/bergamot/restore.ussim is very similar to
pipelines/bergamot/main.ussim, but, rather than a
loadbin command, instead features a restore command:

    ...
    restore /tmp/mainmem.raw /tmp/mainmem.raw.snapshot
    ...

The simulator places the state of the register file into an unused address
inside the main memory snapshot.

## Sample Binary

The sample binary (examples/bin/sum) was created using the RISC-V cross
compiler at https://github.com/riscv-collab/riscv-gnu-toolchain. The source:

    /* examples/src/sum.c */
    #include <stdio.h>

    #include "basics.h"

    int
    main(int argc, char ** argv)
    {
        int retval = 0;
        int x = 1;
        for (; x < argc; x+= 1) retval += atoi(argv[x]);
        return retval;
    }

    /* examples/src/basics.h */
    int atoi(const char *);

    /* examples/src/basics.c */
    int
    atoi(const char * s)
    {
        int retval = 0;
        int x = 0;
        while (s[x] >= 48 && s[x] <= 57) {
            retval *= 10;
            retval += s[x] - 48;
            x += 1;
        }
        return retval;
    }

which is compiled accordingly:

    riscv64-unknown-linux-gnu-gcc -o sum -static -march=rv64g sum.c basics.c

A few things to note: (1) the binary is statically linked, since the
simulator at this stage makes NO effort to accommodate dynamic linking;
(2) the simulator does not use the stdlib's atoi() implementation
since, even with static linking, there are runtime elements (e.g.,
the RISC-V global-pointer register and thread-pointer register) that
are not properly established when execution begins from main(), rather
than _start() (which executes __libc_start_main()); (3) execution from
_start() is a planned feature, but will require a great deal of
additional work on syscall proxying; and (4) because syscall proxying
is not yet complete, there is no printf(), thus, when execution
completes, the sum of all the arguments passed is returned in register
x10, which can be viewed in the simulator's output log.

## Tests

The simulator is capable of loading full, statically-linked ELF binaries,
and also capable of loading ELF-formatted object files. This allows
individual instructions to be tested. Consider, for instance, the test
of the ADDI instruction:

    # tests/src/addi.s
    _start:
            addi x15, x3, 1656
            
The entire assembly language file consists of a single ADDI instruction,
which gets assembled into an object file accordingly

    riscv64-unknown-linux-gnu-as -o addi.o -march=rv64v addi.s

This is **not** a complete binary, but the simulator will nevertheless load
it into memory, set the PC to the address of the _start label, and 
begin execution.