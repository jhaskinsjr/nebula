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

As my doctoral advisor taught me: There are no solutions, only tradeoffs. I
have made this tradeoff knowingly, willingly, intentionally, fully aware of
the performance ramifications to trade away speed for flexibility.