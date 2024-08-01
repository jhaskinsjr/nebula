# Software Architecture

Nebula is a proof-of-concept project intended to gauge the efficacy of
modern microservices software architecture as applied to cycle-accurate
microprocessor simulation. Accordingly, flexibility was prioritized above
performance. For a more detailed discussion
of Nebula's performance, see: [Simulation Speed](./Simulation_Speed.md).

## Philosophy: Simplicity And Flexibility Through Independence

The central design feature of Nebula is that each simulator is
comprised of an army of microservices... independent processes... that
transmit what resources that they require, what information they wish
to communicate, onto the network where all other microservices will
receive it. If something transmitted onto the network matters to one or
more peer microservices, those microservices are free to act upon it and
transmit something back in response.

It likely would have been faster to do point-to-point communication, where
microservices connect directly to the microservice(s) that matter to
them, but this architecture would require every microservice to have detailed
information about every other microservice. This rigidity is the antithesis
of the flexibility that software is meant to facilitate. In other words,
I considered the tradeoff between speed and flexibility, and wilfully,
intentionally chose flexibility.

In addition to flexibility, a significant additional benefit of this design
choice is the incredible simplicity of the software that implements the
pipeline logic. Since each step of executing an instruction (e.g., decode,
register access) is handled by its own service, all the code for each step
is self-contained, making it easier to understand and reason about.

The [Bergamot](pipelines/bergamot/README.md) pipeline's implementation,
for instance, is comprised of five
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

Furthermore, because the units communicate among themselves, it was easy
to construct a unit that monitors communications between the other
units to count events (e.g., number of fetches, number of instructions
flushed, number of instructions retired).

## Communication Channels

There are two main communication channels that the microservices utilize:
`result` and `event`. The
former, as its name implies, is concerned with broadcasting output from the
various microservices, whereas the latter is concerned with broadcasing
requests for actions to be taken. To ask for the value stored in a register,
an `event` is sent, e.g.,

    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid),
        'register': {
            'cmd': 'get',
            'name': _insn.get('rs1'),
        }
    }})

To report the output of an operation, a `result` is sent, e.g.,

    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid),
        'flush': {
            'iid': _insn.get('iid'),
        },
    }})

One general-purpose rule is that incoming `result` messages should
be handled _before_ `event` messages, since `result` messages communicate
information that may be useful in processing `event` messages.

Two other important channels are the `info`
channel, used to echo debug or informational output, e.g., 

    service.tx({'info': '_insn : {}'.format(_insn)})

and the `shutdown` channel used to cleanly cease all of a core's processes
and gracefully exit, e.g., 

    service.tx({'shutdown': {
        'coreid': state.get('coreid'),
    }})

For a complete list, see the handler() function in launcher.py.

## Why Python?

Python is neat, clean, and offers an elegant array of tools to facilitate a
functional programming style. (Consider: `map`, `functools`, `filter`,
`any`, `all`, `itertools`.) Indeed, Python's tools allowed me to quickly
develop the infrastructure that underpins the simulator's design philosophy
of loosely coupled, largely independent services that communicate over a
network in just a couple of weeks, allowing me to rapidly move on to the
more interesting work of developing the actual framework, as well as the
sample pipeline implementations themselves.

In other words, Python allowed
me to rapidly develop the novel concept of microservices-based
cycle-accurate simulation without having to worry about many of the
implementation details I would have had to if I had used C/C++/Rust.

And on top of all that, Python is incredibly **portable**! I do development
work on my Linux laptop, but have received reports from other users that it
also runs seamlessly on MacOS and FreeBSD. And I suspect it runs equally
well on any Unix-like OS with a Python3 port.