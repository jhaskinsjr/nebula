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
RUNNING

If you have not already done so, you will need to install pyelftools; see:

https://github.com/eliben/pyelftools

If you have not already done so, you will need to set up passwordless SSH
access to your host machine; see:

https://www.ibm.com/support/pages/configuring-ssh-login-without-password

Once passwordless SSH has been set up, to quickly run, execute:

cd pipelines/bergamot
python3 launcher.py \
    --max_cycles 32000 \
    --snapshots 1000 \
    --break_on_undefined \
    -- 10000 samples_bin_test_from_main.ussim

First, the "cd" command changes into the subdirectory with the first-ever,
very simple, very primitive μService-SIMulator pipeline implementation,
codename: Bergamot (see: https://en.wikipedia.org/wiki/Bergamot_orange).
The "python3" command then executes the launcher module (launcher.py). The
launcher module will then begin accepting TCP connections on the
localhost's port 10000 and execute the script
sample_bin_test_from_main.ussim, simulating for a maximum of 32,000
simulated cycles, taking snapshots (of the main memory and register file)
every 1,000 simulated cycles, but will cease execution if it encounters an
instruction that is not (yet) defined.

--
SIMULATOR SCRIPTS

The simulator executes according to instructions in an execute script.
Consider the script test-02.ussim:

    # Sample μService-SIMulator script
    service implementation/simplecore.py:localhost
    service implementation/regfile.py:localhost
    service implementation/mainmem.py:localhost
    service implementation/decode.py:localhost
    service implementation/execute.py:localhost
    spawn
    cycle
    loadbin /tmp/mainmem.raw 0x80000000 0x40000000 main ../../samples/bin/test 2 3 5 7 11 13 
                                                            # using /tmp/mainmem.raw as the main memory file,
                                                            # set %sp to 0x80000000 and %pc to 0x40000000, then
                                                            # load samples/bin/test, with command
                                                            # line parameters 2 3 5 7 11 13, and execute
                                                            # beginning from the "main" symbol in the
                                                            # ../../samples/bin/test binary's .text section
    register set 10 0x0                                     # moved by _start into x15 to become rtld_fini;
                                                            # see: https://refspecs.linuxbase.org/LSB_3.1
    run
    cycle
    state
    shutdown

The script is comprised of commands

    cycle                           print the cycle count to stdout
    loadbin A B C D E X             load the binary E with arguments X into main memory file A;
                                    locate stack at address B; locate code at address C; and
                                    begin execution from .text section label D 
    restore A B                     restore previously captured state in B to main memory file A
    register set A B                set register A to value B
    run                             begin execution
    service A:B                     stage service A on machine B
    spawn                           execute all staged services
    state                           print launcher's state (i.e., variables, etc) to stdout
    shutdown                        send shutdown signal to services, exit launcher

The script sample_bin_test_restore.ussim is very similar to
sample_bin_test_from_main.ussim, but, rather than a loadbin command,
instead features a restore command:

    ...
    restore /tmp/mainmem.raw /tmp/mainmem.raw.snapshot
    ...

The simulator places the state of the register file into an unused address
inside the main memory snapshot.

--
SAMPLE binary

The sample binary (samples/bin/test) was created using the RISC-V cross compiler
at https://github.com/riscv-collab/riscv-gnu-toolchain. The source for the
binary is a do-nothing program; to wit:

    /* samples/src/test.c */
    #include <stdio.h>

    int main(int, char **);

    int
    main(int argc, char ** argv)
    {
        return 0;
    }

which is compiled accordingly

    riscv64-unknown-linux-gnu-gcc -o test -static -march=rv64g test.c

Note well that the binary is statically linked; this is key since the
simulator at this stage makes NO effort to accommodate dynamic linking.

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