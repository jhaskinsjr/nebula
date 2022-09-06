# Welcome to μService-SIMulator!

The μService-SIMulator (ussim) is a framework for developing cyce-accurate
microprocessor simulators. Currently, Python libraries for decoding and
executing RISC-V's RV64I instruction set are included. (Most of the
RV64I instruction set, compressed and uncompressed versions of opcode, is
implemented.) In the future, libraries for decoding and executing additional
instruction sets may be added.

## Software Architecture

### Philosophy: Simplicity And Flexibility Through Independence

The central design feature of ussim is that each simulator is
comprised of an army of microservices... independent processes... transmit
what resources that they require, what information they wish to communicate
onto the network where all other microservices will receive it. If something
tarnsmitted onto the network matters to one or more peer microservices,
those microservices are free to act upon it and, where appropriate, transmit
something back in response.

While it would probably be faster to do point-to-point communication, where
microservices connect directly to the microservice(s) that matter to
them, this architecture would require every microservice to have detailed
information about every other microservice. This rigidity is the antithesis
of the flexibility that software is supposed to facilitate. In other words,
I considered the tradeoff between speed and flexibility, and wilfully,
intentionally chose flexibility.

In addition to flexibility, a significant additional benefit of this design
choice is the incredible simplicity of the software that implements the
pipeline logic. Since each step of executing an instruction (e.g., decode,
register access) is handled by its own process, all the code for each step
is self-contained, making it easier to understand and reason about.

The Bergamot pipeline's implementation, for instance, is comprised of five
Python files (see: pipelines/bergamot/implementation/), four of which
contain fewer than 150 lines of code. The lone standout is the file that
handles instruction execution
(see: pipelines/bergamot/implementation/execute.py) which, despite handling
dozens of RISC-V instructions, still contains fewer than 700 lines of code.

These bite-sized units allow chunks of functionality to be cleanly
isolated from one another, making each easier to reason about, easier to
understand, and easier to modify, which is indispensable for implementing
novel design concepts. Consider, for instance, that a change to a function
in the register file logic will almost certainly not alter functionality
implemented in the decoder logic; this reduces the amount of the system
that a developer has to be familiar with in order to be productive.

Furthermore, because the units communicate among themselves, it is easy
to construct a unit that monitors communications between the other
units to count events (e.g., number of fetches, number of instructions
flushed, number of instructions retired).

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

### Why Python

Python is neat, clean, and offers an elegant array of tools to facilitate a
functional programming style. (Consider: `map`, `functools`, `filter`,
`any`, `all`, `itertools`.) Indeed, Python's tools allowed me to quickly
develop the infrastructure that underpins the simulator's design philosophy
of loosely coupled, largely independent processes that communicate over a
network.

With Python, I was able to get the infrastructure developed in just a
couple of weeks, allowing me to rapidly move on to the more interesting work
of developing the actual toolkit for cycle-accurate simulation as well as
the sample pipeline implementations themselves.

And on top of all that, Python is incredibly **portable**! I do development
work on my Linux laptop, but have received reports from other users that it
also runs seamlessly on MacOS. And I suspect it runs equally well on any
Unix-like OS with a Python3 port.

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
number of times each instruction type was executed, etc.

The JSON output file of more sophisticated implementations such as Oroblanco
contain additional statistics about caches and other elements of the
pipeline; e.g.:

    {
        "message_size": {
            "19": 1,
            "18": 1,
            "150": 1,
            ...
            "972": 1,
            "890": 1
        },
        "cycle": 14872,
        "fetch": {
            "l1ic.misses": 35,
            "l1ic.accesses": 3929
        },
        "l2": {
            "l2.misses": 55,
            "l2.accesses": 385
        },
        "mainmem": {
            "peek.size": {
                "16": 55
            },
            "poke.size": {
                "8": 57,
                "4": 264
            }
        },
        "decode": {
            "decoded.insn": {
                "ADDI": 759,
                "SD": 85,
                "SW": 264,
                "JAL": 68,
                "LW": 607,
                "SLLI": 28,
                ...
                "SUBW": 27,
                "JALR": 28
            },
            "issued.insn": {
                "ADDI": 692,
                "SD": 57,
                "SW": 264,
                "JAL": 68,
                "LW": 607,
                ...
                "JALR": 28,
                "SUBW": 13
            }
        },
        "regfile": {
            "get.register": {
                "2": 170,
                "1": 29,
                "8": 1265,
                "10": 82,
                "11": 1,
                "15": 1829,
                "14": 626
            },
            "set.register": {
                "2": 56,
                "8": 56,
                "15": 1829,
                "0": 68,
                "14": 575,
                "10": 55,
                "1": 28
            }
        },
        "alu": {
            "category": {
                "do_itype": 1073,
                "do_store": 321,
                "do_jal": 68,
                "do_load": 1235,
                "do_branch": 184,
                "do_shift": 129,
                "do_rtype": 376,
                "do_jalr": 28
            }
        },
        "commit": {
            "retires": 3173,
            "flushes": 240,
            "speculative_next_pc": 241,
            "speculative_next_pc_correct": 180
        },
        "lsu": {
            "l1dc.misses": 29,
            "l1dc.accesses": 1556
        }
    }

The JSON struct has 10 top-level keys: `message_size`, `cycle`, `fetch`,
`l2`, `mainmem`, `decode`, `regfile`, `alu`, `commit` `lsu`. The
`message_size` entry contains a histogram of the sizes of the messages
passed between the various components, and `cycle` contains the count
of simulated cycles when the simulator exited. The final eight keys
correspond to pipeilne components of the same names, and offer statistcs
about number of cache misses, cache accesses, number of times each
register was read/written, number of instructions retired/flushed, etc.

## Pipeline Designs

At present, there are four pipeline implementations: Bergamot, Clementine,
Lime, and Oroblanco.

The Running section above shows how to execute the examples/bin/sum program
using the Bergamot implementation; to use the Clementine implementation,
"cd" into the pipelines/clementine subdirectory (instead of
pipelines/bergamot); to use the Lime implementation, "cd" into the
pipelines/lime subdirectory; to use the Oroblanco implementation, "cd" into
the pipelines/oroblanco subdirectory.

For a brief overview of each pipeline implmentation, follow the links below:

* [Bergamot](pipelines/bergamot/README.md)
* [Clementine](pipelines/clementine/README.md)
* [Lime](pipelines/lime/README.md)
* [Oroblanco](pipelines/oroblanco/README.md)

## Simulator Scripts

The simulator executes according to instructions in an execute script.
Consider the script pipelines/oroblanco/main.ussim:

    # Sample μService-SIMulator script
    service implementation/simplecore.py:localhost
    service implementation/regfile.py:localhost
    service implementation/mainmem.py:localhost
    service implementation/decode.py:localhost
    service implementation/execute.py:localhost
    spawn
    config mainmem peek_latency_in_cycles 25
    config fetch l1ic.nsets 16
    config fetch l1ic.nways 2
    config fetch l1ic.nbytesperblock 16
    config fetch l1ic.evictionpolicy lru # random
    config decode buffer_capacity 16
    config decode btb.nentries 8
    config decode btb.nbytesperentry 8
    config decode btb.evictionpolicy lru # random
    config alu forwarding True
    config lsu l1dc.nsets 16
    config lsu l1dc.nways 2
    config lsu l1dc.nbytesperblock 16
    config lsu l1dc.evictionpolicy lru # random
    config l2 l2.nsets 32
    config l2 l2.nways 16
    config l2 l2.nbytesperblock 16
    config l2 l2.evictionpolicy lru # random
    config l2 l2.hitlatency 5
    config stats output_filename /tmp/stats.json
    # Memory hierarhchy peek latencies...
    # - L1 peek-hit latency: 5**0 cycles
    # - L2 peek-hit latency: 5**1 cycles
    # - MM peek     latency: 5**2 cycles
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

## Sample Binaries

The sample binaries... examples/bin/sum, examples/bin/sort,
examples/bin/negate, and examples/bin/test... were created using the RISC-V
cross compiler at https://github.com/riscv-collab/riscv-gnu-toolchain.
Consider the source for the sum program:

```
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
```
```
    /* examples/src/basics.h */
    int atoi(const char *);
```
```
    /* examples/src/basics.c */
    int
    atoi(const char * s)
    {
        int retval = 0;
        int x = 0;
        while (s[x] >= '0' && s[x] <= '9') {
            retval *= 10;
            retval += s[x] - '0';
            x += 1;
        }
        return retval;
    }
```

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
x10, which can be viewed in the regile.py output log.

## Simulator Speed

On my laptop, a Lenovo ThinkPad with 32 GB of RAM and an Intel Core
i7-8565U, running Ubuntu MATE 22.04, the Oroblanco pipeline executes at a
rate of about 30 simulated cycles per real-world second at a steady state
system load of less than 10%.

While 30 cycles/second is not blazingly fast,
as stated above (see: Software Architecture), I view the flexibilty
enabeld by this software architecture as a more-than-worthwhile tradeoff.
Also, consider that with the CPU utilization so low, I am able to execute
many simulations simulatenously without saturating my CPU; this
comports well with the fact that much of microarchitecture research
requires large state-space searches, with many executions of the same
benchmarks under different parameters (e.g., cache capacity, cache
replacement algorithm, branch predictor).
Finally, consider that I have made almost no effort to optimize the
simulator, choosing instead at this early stage to focus primarily on
correctness; future optimization efforts will doubtless increase the
execution speed.

## Instruction Implementation Tests

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

## Future Features

Presented in no particular order, here are some additional features that will
extend and enhance the simulator:

1. pipeline implementation with value prediction
1. syscall proxying
1. launch from binary's `_start` label rather than `main` label
1. tool for cataloging, indexing, and retrieval of simulator runs
1. `clone`-based perfect branch predictor
1. `clone`-based perfect value predictor
1. return address stack
1. accelerated `mmap`-based main memory implementation
1. implement new eviction policies (e.g., least frequently used) for SimpleCache
and SimpleBTB
1. include additional example benchmarks
1. pipeline implementation with decoupled fetch engine
1. pipeline implementation with out-of-order execution
1. multi-core support with cache sharing
1. MIPS instruction set support
1. x86_64 instruction set support
1. SPARC instruction set support

That said, since this is a toolkit intended to facilitate microarchitecture
research, some of these, as my math textbooks used to say, "will be left as
an exercise" for researchers.

## Reaching The Author

I can be reached at https://www.linkedin.com/in/john-haskins-jr-925235a1/
and john.haskins.jr@gmail.com.

If you use this simulator toolkit, please do reach out. I would love to
hear from you!