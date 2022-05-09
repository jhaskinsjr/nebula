Welcome to μService-SIMulator!

The central premise of ussim is that an army of microservices shout out
whatever they need, whatever information they which to communicate, whatever
matters to them into the wide-open "ether." All microservices are connected
to the same ether, constantly listening thereto. If something shouted into
the ether matters to one or more microservices, they are free to act upon it
and, where appropriate, shout something in response back into the ether.

THIS IS AN INTENTIONAL DESIGN CHOICE!

While it would probably be faster to do point-to-point communication, where
microservices communicate directly to the microservice(s) that matter to
them, this architecture would require every microservice to have detailed
information about every other microservice. This rigidity is the antithesis
of the flexibility that software is supposed to facilitate.

There are no solutions, only tradeoffs. I have made this tradeoff knowingly,
willingly, intentionally, fully aware of the performance ramifications.
Notwithstanding this, I chose to trade away speed for flexibility.

--
SOFTWARE architecture

As mentioned in the preceding section, ussim uses a collection of
independent microservices, each with its own task (e.g., fetch instruction
bytes, service register file operations), all communicating over a shared
"party line," implemented over TCP.

There are two main communication channels: "results" and "events." The
former, as its name implies, is concerned with broadcasting output from the
various microservices, whereas the latter is concerned with broadcasing
requests for actions to be taken. To ask for the value stored in a register,
an event is sent, e.g.,

    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'get',
            'name': _insn.get('rs1'),
        }
    }})

To report the result of an operation, a result is sent, e.g.,

    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'flush': {
            'iid': _insn.get('iid'),
        },
    }})

One general-purpose rule of thumb is that incoming results should be handled
BEFORE events, since results communicate information that may be useful in
processing events.

There are other channels as well; two highlights are the "info" channel, used
to echo debug/informational output, e.g., 

    service.tx({'info': '_insn : {}'.format(_insn)})

and the "shutdown" channel used to cleanly cease all ussim processes and
gracefully exit, e.g., 

    service.tx({'shutdown': None})

For a complete list, see the handler() function in launcher.py.

--
RUNNING

If you have not already done so, you will need to install pyelftools; see:

https://github.com/eliben/pyelftools

If you have not already done so, you will need to set up passwordless SSH
access to your host machine; see:

https://www.ibm.com/support/pages/configuring-ssh-login-without-password

Once passwordless SSH has been set up, to quickly run, execute:

cd pipelines/bergamot
python3 ../../launcher.py \
    --max_cycles 32000 \
    --snapshots 1000 \
    --break_on_undefined \
    -- \
    main.ussim \
    ../../examples/bin/sum 2 3 5 7 11 13

First, the "cd" command changes into the subdirectory with the first-ever,
very simple, very primitive μService-SIMulator pipeline implementation,
codename: Bergamot (see: https://en.wikipedia.org/wiki/Bergamot_orange).
The "python3" command then executes the launcher module (launcher.py). The
launcher module will then begin by executing the script main.ussim, and
loading the binary "../../examples/bin/sum" together with its command-line
parameters "2 3 5 7 11 13", into the simulator's main memory; and simulating
for a maximum of 32,000 simulated cycles, taking snapshots (of the
simulated main memory and register file) every 1,000 simulated cycles, but
will cease execution if it encounters an instruction that is not (yet)
defined.

--
PIPELINE DESIGNS

At present, there are two pipeline implementations: Bergamot and Clementine.

The RUNNING section above executes the examples/bin/sum program using the
Bergamot implementation; to use the Clementine implementation instead, "cd"
into the pipelines/clementine subdirectory (instead of pipelines/bergamot).

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
the consumer until the producer either retires or is flushed by the commit
stage. Control-flow hazards are handled by the commit stage, which, when a
jump (JAL, JALR) or a taken branch (BEQ, BNE, BGE, BLT, BGEU, BLTU)
instruction retires; when this happens, the new PC is reported, which is
sensed by the instruction fetch stage and the decode stage. The instruction
fetcher responds by beginning to fetch instruction bytes from the new PC;
the decoder responds by flushing all previously-decoded instructions.
Finally, the commit stage will continue to flush all instructions following
the jump/taken branch until it receives an instruction with the target PC.

--
SIMULATOR SCRIPTS

The simulator executes according to instructions in an execute script.
Consider the script main.ussim:

    # Sample μService-SIMulator script
    port 10000
    service implementation/simplecore.py:localhost
    service implementation/regfile.py:localhost
    service implementation/mainmem.py:localhost
    service implementation/decode.py:localhost
    service implementation/execute.py:localhost
    spawn
    cycle
    loadbin /tmp/mainmem.raw 0x80000000 0x40000000 main # using /tmp/mainmem.raw as the main memory file,
                                                        # set x2 to 0x80000000 and %pc to 0x40000000, then
                                                        # load binary (e.g., ../../examples/bin/sum), and,
                                                        # optionally, command line parameters (e.g.,
                                                        # 2 3 5 7 11 13), and execute beginning from the
                                                        # "main" symbol in the binary's .text section

    run
    cycle
    state
    shutdown

The script is comprised of commands

    cycle                           print the cycle count to stdout
    loadbin A B C D E X             set main memory file A; locate stack at address B; locate code
                                    at address C; and begin execution from .text section label D 
    port A                          set simulator to accept connections at port A
    restore A B                     restore previously captured state in B to main memory file A
    register set A B                set register A to value B
    run                             begin execution
    service A:B                     stage service A on machine B
    spawn                           execute all staged services
    state                           print launcher's state (i.e., variables, etc) to stdout
    shutdown                        send shutdown signal to services, exit launcher

The script restore.ussim is very similar to main.ussim, but, rather than a
loadbin command, instead features a restore command:

    ...
    restore /tmp/mainmem.raw /tmp/mainmem.raw.snapshot
    ...

The simulator places the state of the register file into an unused address
inside the main memory snapshot.

--
SAMPLE binary

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

which is compiled accordingly

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
x10, which can be viewed in the simulator's output log (2 + 3 + 5 + 7
+ 11 + 13 = 41).

--
TESTS

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

This is NOT a complete binary, but the simulator will nevertheless load
it into memory, set the PC to the address of the _start label, and 
begin execution.