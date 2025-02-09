# Software Architecture

Nebula is a project intended to gauge the efficacy of
modern microservices software architecture as applied to cycle-accurate
microprocessor simulation.

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

## Granularity

The Nebula sample pipeline models are use either per-component
granularity or per-core granuylarity.

With per-component granularity,
each of a pipeline's various elements (e.g., decoder, register file)
is spawned inside its own independent Python process.
An apt example of per-component granularity is the
[Bergamot](../pipelines/bergamot/README.md) pipeline model, which is
comprised of five Python files (see: pipelines/bergamot/implementation/).
When a Bergamot simulation executes all five... simplecore.py, decode.py,
regfile.py, execute.py, and watchdog.py... are executed as independent
processes that communicate with each other over a TCP network.

On the other hand, [Etrog](../pipelines/etrog/README.md) uses per-core
granularity. Like Bergamot, Etrog's implementation is also comprised of
several Python files (see: pipelines/etrog/implementation/). However,
rather than spawning each as its own Python process, only core.py is
executed, and it, in turn, `import`s the other Python files and
instantiates an object from each; messages are then passed between these
objects over an internal "network," with only a small subset of those
messages, e.g., communication with main memory, being communicated
outside of core.py. Etrog, in essence, is a reimplementation of Bergamot
that executes much more rapidly... almost 6 times faster than Betgamot...
because of much less interprocess communication.

When Nebula was first developed, all the sample pipeline models
utilized per-component granularity. Per-core granularity emerged in
release 1.5.0, with [Etrog](../pipelines/etrog/README.md), followed by
[Tangerine](../pipelines/tangerine/README.md), which is a per-core
reimplementation of [Tangelo](../pipelines/tangelo/README.md) in release
2.0.0. Note that while Tangerine encapsulates each _core_'s components
inside a single process, L2s and L3s continue to be executed inside
independent processes so that they, like main memory, may be easily
shared across multiple cores in multicore simulations.

Moving forward, future sample pipeline models will use per-core
granularity.

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