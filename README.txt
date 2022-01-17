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

python3 launcher.py --services \
    ${PWD}/simplecore.py:localhost \
    ${PWD}/regfile.py:localhost \
    ${PWD}/mainmem.py:localhost \
    ${PWD}/decode.py:localhost \
    --max_cycles 100 \
    -- 10000 test-01.ussim

This executes the launcher module (launcher.py), which in turn spawns the
CPU core service (simplecore.py), the register file service (regfile.py), and
the main memory service (mainmem.py), all on localhost. The simulation will
run for a total of 100 cycles, set up the launcher module to accept
TCP connections on the localhost's port 10000, and execute the script
test-01.ussim.