# Nebula: The Cloud-Native Microarchitecture Simulation Framework!

Nebula (formerly: μService-SIMulator (ussim)) is a framework for
developing cycle-accurate microprocessor simulators. Python libraries for
decoding and executing statically linked RISC-V binaries, as well as
several sample pipeline implementations using the framework are included.

# Quick Start

**Step 1.** Clone the git repo:

    mkdir -p ${HOME}/src
    cd ${HOME}/src
    git clone https://github.com/jhaskinsjr/nebula.git

**Step 2.** Install `pyelftools`:

    pip3 install pyelftools

**Step 3.** Set up passwordless SSH access to your host machine. A guide
for doing this can be found at

https://www.ibm.com/support/pages/configuring-ssh-login-without-password

**Step 4.** Create a folder for the execution artifacts:

    mkdir -p /tmp/pompia/sum

**Step 5.** Enter the directory of one of the sample pipelines; for this
example, we will use the Pompia pipeline:

    cd ${HOME}/src/nebula/pipelines/pompia

**Step 6.** Execute:

    python3 ../../launcher.py \
        --log /tmp/pompia/sum \
        --service ../../toolbox/stats.py:localhost:-1 implementation/mainmem.py:localhost:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        init.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13

The "python3" command executes the Nebula launcher (launcher.py),
which begins by opening a socket and accepting connections on port 12345,
executing the script init.nebula, and loading the binary
(${HOME}/src/nebula/examples/bin/sum) together with its command-line
parameters "2 3 5 7 11 13", into the simulated main memory. With this
foundation established, the simulator will execute a maximum of 100,000
simulated instructions.

**Step 7.** Examine the output:

The output emitted to the console from the simulator should be 41, the sum
of the first six prime integers; to wit:

    41

For a more in-depth analysis of the actions taken by the simulator,
each module emits its own log file:

* **/tmp/pompia/sum/launcher.py.log**: detailed
information about the operation of the Pompia pipeline
* **/tmp/pompia/sum/mainmem.py.log**: loading the binary and placing the
command line arguments
* **/tmp/pompia/sum/stats.py.log**: module configuration and the final
JSON object
* **/tmp/pompia/sum/0000_regfile.py.log**: initial- and final states of
the register file on core 0
* **/tmp/pompia/sum/0000_alu.py.log**: instructions that executed
on core 0 (irrespective of whether they ultimately retire)
* **/tmp/pompia/sum/0000_commit.py.log**: all instructions that
retired on core 0
* **/tmp/pompia/sum/stats.json**: counts of key events that occurred
during the simulation for each core

These log files assist with debugging and gaining deeper insights about the
operation of the simulator and the pipeline designs that the simulator
models. Some modules' log files (e.g., 0000_fetch.py.log,
0000_decode.py.log) will be empty. This does not signify a malfunction; the
module just did not report on any events, but could be modified to do so. 

## JSON Output

Consider the following example stats.json output (gathered by executing
a 3SAT solver sample binary on Pompia):

```
{
  "message_size": {
    "19": 1,
    "18": 1,
    "150": 1,
    ...
    "972": 1,
    "890": 1,
  },
  "cycle": 129550,
  "0": {
    "fetch": {
      "l1ic_misses": 12035,
      "l1ic_accesses": 29547
    },
    "l2": {
      "l2_misses": 1229,
      "l2_accesses": 18064
    },
    "decode": {
      "decoded.insn": {
        "ADD": 4834,
        "JAL": 2456,
        "LW": 2067,
        ...
        "MUL": 6,
        "SLLW": 2,
        "SRAI": 1
      },
      "issued.insn": {
        "ADD": 3546,
        "JAL": 2022,
        "LW": 1890,
        ...
        "MUL": 4,
        "SLLW": 2,
        "SRAI": 1
      }
    },
    "regfile": {
      "get.register": {
        "0": 5587,
        "25": 230,
        "8": 5074,
        ...
        "27": 98,
        "28": 28,
        "30": 14
      },
      "set.register": {
        "11": 688,
        "1": 914,
        "15": 6394,
        ...
        "16": 713,
        "30": 14,
        "17": 77
      }
    },
    "alu": {
      "category": {
        "do_rtype": 4486,
        "do_jal": 2022,
        "do_load": 9965,
        "do_branch": 3366,
        "do_itype": 6929,
        "do_store": 4326,
        "do_jalr": 971,
        "do_nop": 336,
        "do_lui": 700,
        "do_shift": 1230,
        "do_ecall": 6
      }
    },
    "commit": {
      "retires": 27828,
      "flushes": 6507
    },
    "lsu": {
      "l1dc_misses": 1945,
      "l1dc_accesses": 11772
    }
  },
  "-1": {
    "mainmem": {
      "peek.size": {
        "16": 1229,
        "153": 1
      },
      "poke.size": {
        "1": 142,
        "4": 400,
        "8": 3535,
        "2": 8
      }
    }
  }
}
```

The JSON struct has several top-level keys including: `message_size`, `cycle`,
`0`, and `-1`. The`message_size` entry contains a histogram of the sizes of
the messages passed between the various components, and `cycle` contains the
count of simulated cycles when the simulator exited. `0` contains several
sub-keys corresponding to the pipeline components on simulated core 0:
`fetch`, `l2`, `mainmem`, `decode`, `regfile`, `alu`, `commit`, `lsu`. They
offer statistics about the number of cache misses, cache accesses, number of
times each register was read/written, number of instructions retired/flushed,
etc.
Finally, `-1` contains sub-keys corresponding to components that are
accessible by all simulated cores, in this case, only `mainmem`.

# Software Architecture

## Philosophy: Simplicity And Flexibility Through Independence

The central design feature of Nebula is that each simulator is
comprised of an army of microservices... independent processes... that
transmit what resources that they require, what information they wish
to communicate, onto the network where all other microservices will
receive it. If something tarnsmitted onto the network matters to one or
more peer microservices, those microservices are free to act upon it and
transmit something back in response.

While it might be faster to do point-to-point communication, where
microservices connect directly to the microservice(s) that matter to
them, this architecture would require every microservice to have detailed
information about every other microservice. This rigidity is the antithesis
of the flexibility that software is supposed to facilitate. In other words,
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

and the `shutdown` channel used to cleanly cease all Nebula processes and
gracefully exit, e.g., 

    service.tx({'shutdown': None})

For a complete list, see the handler() function in launcher.py.

## Why Python?

Python is neat, clean, and offers an elegant array of tools to facilitate a
functional programming style. (Consider: `map`, `functools`, `filter`,
`any`, `all`, `itertools`.) Indeed, Python's tools allowed me to quickly
develop the infrastructure that underpins the simulator's design philosophy
of loosely coupled, largely independent services that communicate over a
network.

With Python, I was able to get the infrastructure developed in just a
couple of weeks, allowing me to rapidly move on to the more interesting work
of developing the actual toolkit for cycle-accurate simulation as well as
the sample pipeline implementations themselves.

And on top of all that, Python is incredibly **portable**! I do development
work on my Linux laptop, but have received reports from other users that it
also runs seamlessly on MacOS and FreeBSD. And I suspect it runs equally
well on any Unix-like OS with a Python3 port.

# Sample Pipelines

At present, there are seven sample pipeline implementations: Amanatsu,
Bergamot, Clementine, Lime, Oroblanco, Pompia, and Rangpur.

The Quick Start section above shows how to execute the examples/bin/sum program
using the Pompia implementation; to use the Amanatsu implementation, "cd"
into the pipelines/amanatsu subdirectory (instead of pipelines/pompia); to
use the Bergamot implementation, "cd" into the pipelines/bergamot subdirectory;
etc.

For a brief overview of each pipeline implmentation, follow the links below:

* [Amanatsu](pipelines/amanatsu/README.md)
* [Bergamot](pipelines/bergamot/README.md)
* [Clementine](pipelines/clementine/README.md)
* [Lime](pipelines/lime/README.md)
* [Oroblanco](pipelines/oroblanco/README.md)
* [Pompia](pipelines/pompia/README.md)
* [Rangpur](pipelines/rangpur/README.md)

# Snapshots

The [Amanatsu] (pipelines/amanatsu/README.md) pipeline implementation does
not actually model a pipeline. Rather, it fetches and executes instructions
in a tight loop as rapidly as possible. In addition to making it almost 1,000
times faster than any of the other sample pipelines (all of which, do model
execution in cycle-accurate detail), this makes Amanatsu ideally suited for
capturing execution state in a snapshot that can be resumed.

## Capturing A Snapshot

To capture snapshots after 100, 300, 900, and 2,700 instructions' worth of
execution:

    cd  ${HOME}/src/nebula/pipelines/amanatsu/
    mkdir -p /tmp/amanatsu/sum
    python3 ../../launcher.py \
        --log /tmp/amanatsu/sum \
        --service ../../toolbox/stats.py:localhost:-1 \
        --config stats:output_filename:/tmp/amanatsu/sum/stats.json \
        mainmem:filename:/tmp/amanatsu/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --snapshots 100 300 900 2700 \
        -- \
        12345 \
        init.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 17 19 23 29

This will create a series of files:

* **/tmp/amanatsu/sum/mainmem.raw.000000000000100.snapshot**: execution state captured after 100 instructions
* **/tmp/amanatsu/sum/mainmem.raw.000000000000300.snapshot**: execution state captured after 300 instructions
* **/tmp/amanatsu/sum/mainmem.raw.000000000000900.snapshot**: execution state captured after 900 instructions
* **/tmp/amanatsu/sum/mainmem.raw.000000000002700.snapshot**: execution state captured after 2,700 instructions

## Restoring From A Snapshot

Any of the pipelines can restore state from a snapshot and resume execution,
e.g.:

    cd  ${HOME}/src/nebula/pipelines/pompia/
    python3 ../../launcher.py \
        --log /tmp/pompia/sum \
        --service ../../toolbox/stats.py:localhost:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --restore /tmp/amanatsu/sum/mainmem.raw.000000000000900.snapshot \
        -- \
        12345 \
        init.nebula

Note: (1) the `--restore` parameter is included; and (2) the command that
was executed to create the snapshots (`../../examples/bin/sum 2 3 5 7 11 13 17 19 23 29`...) is
omitted. In this example, the Pompia pipeline should return

    129

On my laptop, resuming from this snapshot, Pompia finishes executing in
a little more than 8 minutes, whereas executing the same command line
end-to-end, Pompia requires more than 11 minutes.

# Simulator Scripts

The simulator executes according to instructions in an execute script.
Consider the script pipelines/pompia/init.nebula:

    # Sample μService-SIMulator script
    # NOTE: Nebula's multicore support can execute across multiple machines!
    # core 0
    service implementation/regfile.py:localhost:0
    service implementation/fetch.py:localhost:0
    service implementation/decode.py:localhost:0
    service implementation/alu.py:localhost:0
    service implementation/lsu.py:localhost:0
    service implementation/commit.py:localhost:0
    service implementation/l2.py:localhost:0
    ## core 1
    #service implementation/regfile.py:localhost:1
    #service implementation/fetch.py:localhost:1
    #service implementation/decode.py:localhost:1
    #service implementation/alu.py:localhost:1
    #service implementation/lsu.py:localhost:1
    #service implementation/commit.py:localhost:1
    #service implementation/l2.py:localhost:1
    spawn
    config mainmem:peek_latency_in_cycles 25
    config fetch:l1ic_nsets 16
    config fetch:l1ic_nways 2
    config fetch:l1ic_nbytesperblock 16
    config fetch:l1ic_evictionpolicy lru # random
    config decode:max_instructions_to_decode 4
    config l2:l2_nsets 32
    config l2:l2_nways 16
    config l2:l2_nbytesperblock 16
    config l2:l2_evictionpolicy lru # random
    config l2:l2_hitlatency 5
    config mainmem:peek_latency_in_cycles 25
    config mainmem:filename /tmp/mainmem.raw
    config mainmem:capacity 4294967296
    config stats:output_filename /tmp/stats.json
    run
    shutdown

The script is comprised of commands

    config A B C                    change configuration of service A field B to value C
    cycle                           print the cycle count to stdout
    register set A B                set register A to value B
    run                             begin execution
    service A:B:C                   stage service A on machine B as a part of core C
    spawn                           execute all staged services
    state                           print launcher's state (i.e., variables, etc) to stdout
    shutdown                        send shutdown signal to services, exit launcher

# Distributed Simulations

Because the μService-SIMulator framework spawns multiple independent
services that communicate over a TCP network, the services need not execute
on the same machine. This is what makes μService-SIMulator
**the world's first cloud-native microarchitecture simulation framework**!

Consider the following modified Pompia init.nebula file that
spawns services on several different machines on my network:

    # Sample μService-SIMulator script
    service implementation/regfile.py:picard.local:0   # not run on localhost!
    service implementation/fetch.py:riker.local:0      # not run on localhost!
    service implementation/decode.py:laforge.local:0   # not run on localhost!
    service implementation/alu.py:data.local:0         # not run on localhost!
    service implementation/lsu.py:worf.local:0         # not run on localhost!
    service implementation/commit.py:troi.local:0      # not run on localhost!
    service implementation/l2.py:crusher.local:0       # not run on localhost!
    spawn
    config mainmem:peek_latency_in_cycles 25
    config fetch:l1ic_nsets 16
    config fetch:l1ic_nways 2
    config fetch:l1ic_nbytesperblock 16
    config fetch:l1ic_evictionpolicy lru # random
    config decode:max_instructions_to_decode 4
    config l2:l2_nsets 32
    config l2:l2_nways 16
    config l2:l2_nbytesperblock 16
    config l2:l2_evictionpolicy lru # random
    config l2:l2_hitlatency 5
    config stats:output_filename /tmp/stats.json
    run
    shutdown

Recall that the mainmem.py and stats.py services are spawned locally using
the "--service" command line parameter.

# Multicore Simulations

Nebula also supports multicore simulations, and can place the services for
each core on a single machine, and accommodate multiple cores spanning
multiple machines. Consider the following modified Pompia init.nebula:

    # Sample μService-SIMulator script
    # core 0
    service implementation/regfile.py:picard.local:0   # not run on localhost!
    service implementation/fetch.py:picard.local:0     # not run on localhost!
    service implementation/decode.py:picard.local:0    # not run on localhost!
    service implementation/alu.py:picard.local:0       # not run on localhost!
    service implementation/lsu.py:picard.local:0       # not run on localhost!
    service implementation/commit.py:picard.local:0    # not run on localhost!
    service implementation/l2.py:picard.local:0        # not run on localhost!
    # core 1
    service implementation/regfile.py:riker.local:1    # not run on localhost!
    service implementation/fetch.py:riker.local:1      # not run on localhost!
    service implementation/decode.py:riker.local:1     # not run on localhost!
    service implementation/alu.py:riker.local:1        # not run on localhost!
    service implementation/lsu.py:riker.local:1        # not run on localhost!
    service implementation/commit.py:riker.local:1     # not run on localhost!
    service implementation/l2.py:riker.local:1         # not run on localhost!
    spawn
    config mainmem:peek_latency_in_cycles 25
    config fetch:l1ic_nsets 16
    config fetch:l1ic_nways 2
    config fetch:l1ic_nbytesperblock 16
    config fetch:l1ic_evictionpolicy lru # random
    config decode:max_instructions_to_decode 4
    config l2:l2_nsets 32
    config l2:l2_nways 16
    config l2:l2_nbytesperblock 16
    config l2:l2_evictionpolicy lru # random
    config l2:l2_hitlatency 5
    config stats:output_filename /tmp/stats.json
    run
    shutdown

Thus, all the services for core 0 are executed on the server picard.local,
and all the services for core 1 are executed on the server riker.local.
Both cores are Pompia cores, and both are identically configured. Both
will commence execution when the init.nebula "run" command is executed by
the launcher.

To execute across N cores, it is necessary to supply N binaries and their
parameters, e.g.:

    python3 ../../launcher.py \
        --log /tmp/pompia/sum \
        --service ../../toolbox/stats.py:localhost:-1 implementation/mainmem.py:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        init.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13 , ../../examples/bin/sort 7 2 3 5

where each binary-parameter set is separated by a comma.

As the binaries execute, a rudimentary MMU (see: components/simplemmu/) will
map addresses from core 0 to separate addresses from core 1 so that the two
simulations can proceed concurrently without clobbering one another's state.

# Sample Binaries

The sample binaries...

* examples/bin/sum
* examples/bin/sort
* examples/bin/negate
* examples/bin/puts
* examples/bin/cat
* examples/bin/3sat

were created using the RISC-V
cross compiler at https://github.com/riscv-collab/riscv-gnu-toolchain,
following the directions under the "Installation (Newlib)" section; see:
https://github.com/riscv-collab/riscv-gnu-toolchain#installation-newlib. (It
would be a *lot* more work to execute binaries built for Linux, i.e.,
following the directions under the "Installation (Linux)" section.)
Consider the source for the sum program:

    /* examples/src/sum.c */
    #include <stdio.h>
    #include <stdlib.h>

    int
    main(int argc, char ** argv)
    {
        int sum = 0;
        int x = 1;
        for (; x < argc; x+= 1) sum += atoi(argv[x]);
        printf("%d\n", sum);
        return 0;
    }

which is compiled accordingly:

    riscv64-unknown-elf-gcc -o sum -static -march=rv64g sum.c

Please note that the binary is statically linked, since the simulator at
this stage makes NO effort to accommodate dynamic linking.

# Running Large-Scale Studies

If you have not already done so, install pymongo; see:
https://pypi.org/project/pymongo/.

Microarchitecture research tends to involve large state-space searches
comprised of many thousands or even millions of different configurations of
the caches, the branch predictor, decoder, etc. Manually launching such
large numbers of experiments is a significant challenge.

Therefore, to facilitate large-scale studies, the μService-SIMulator
includes `executor.py`, which takes as input a JSON-formatted expression of
the state space to be explored. Consider the included `executor.py` script
l1ic_size.exec:

```
{
    "pipelines/lime": {
        "mainmem": 4297967296,
        "config": {
            "fetch:l1ic_nsets": [16, 64],
            "fetch:l1ic_nways": [2, 4],
            "fetch:l1ic_nbytesperblock": [16, 32],
            "fetch:l1ic_evictionpolicy": ["random", "lru"],
            "l2:l2_nbytesperblock": [64]
        },
        "max_cycles": 32000,
        "snapshots": 1000,
        "break_on_undefined": true,
        "script": "init.nebula",
        "command": "../../examples/bin/sum 2 3 -5 7"
    },
    "pipelines/oroblanco": {
        "mainmem": 4297967296,
        "config": {
            "fetch:l1ic_nsets": [16, 64],
            "fetch:l1ic_nways": [2, 4],
            "fetch:l1ic_nbytesperblock": [16, 32],
            "fetch:l1ic_evictionpolicy": ["random", "lru"],
            "l2:l2_nbytesperblock": [64]
        },
        "max_cycles": 32000,
        "snapshots": 1000,
        "break_on_undefined": true,
        "script": "init.nebula",
        "command": "../../examples/bin/sum 2 3 -5 7"
    }
}
```

This script spawns runs of two pipelines: Lime and Oroblanco, the only two
pipelines that have L1 instruction caches. Separate runs will be spawned
for the cross product of two configurations of the number of sets (16 or
64), the number of ways (2 or 4), the number of bytes/block (16 or 32),
the eviction policy (LRU or random); for a total of 16 configurations for
Lime and 16 configurations for Oroblanco. To execute the all 32 runs, from
the top-level directory of the source tree, execute:

```
mkdir /tmp/runs
python3 ./executor.py \
    --purge_successful \
    --basepath /tmp/runs \
    --stochastic 0.5 \
    --max_cpu_utilization 80 \
    -- \
    l1ic_size.exec
```

The first parameter, `--purge_successful`, will delete from the file system
the artifacts (e.g., log files, the mainmem file, stats.json) produced by
each execution of the simulator that returns error code 0. The `--basepath`
parameter
points to the place for all the file system artifacts to be deposited during
the execution of the simulations; default: /tmp. The `--stochastic` parameter
sets the approximate probability that each run will execute, so that only a
random subset of the cross product of runs executes; default 1 (i.e., launch
100% of the runs).  The `--max_cpu_utilization`
parameter caps the CPU utilization so that many thousands of simulations do
not launch simultanesouly and cripple the system that the simulations are
running on; default: 90. And, `l1ic_size.exec` is the input to
`executor.py`.

Finally, since wrangling all the output generated by the simulations is
also a significant challenge, `exeuctor.py` also includes simple support
for inserting artifacts of each simulation into a MongoDB
(see: https://www.mongodb.com/) database; to wit:

```
mkdir /tmp/runs
python3 ./executor.py \
    --purge_successful \
    --basepath /tmp/runs \
    --max_cpu_utilization 80 \
    --stochastic 0.5 \
    --mongodb mongodb://citrus.local:27017 nebula experiments \
    -- \
    l1ic_size.exec
```

This command line operates identically to the preceding, but also inserts
documents into the MongoDB server running on my internal network named
`citrus.local` at port `27017`, in a database named `nebula`, in a collection
named `experiments`. It inserts one document per configuration, and the
documents contain all the data generated by the simulation execution
(i.e., its stats.json) and important metadata about the simulation
including the date, time, the Git SHA of the source tree, the branch of
the source tree, the exit code, the log files generated by the execution,
the configuration used by the simulation, the path within which the
execution artifacts were deposited during the execution, the pipeline
that executed, the simulator execution script (e.g., init.nebula), and the
command line to invoke the simulation.

# Simulator Speed

On my laptop, a Lenovo ThinkPad with 32 GB of RAM and an Intel Core
i7-8565U, running Ubuntu MATE 22.04, Amanatsu executes at a rate of
approximately 4,000 instructions/second. Recall, however, that Amanatsu does
**not** perform cycle-accurate simulation, but, rather, merely executes
instructions in a tight loop, updating state (main memory and the register
file) as rapidly as possible. This is what makes Amanatsu ideal for
creating simulation snapshots for subsequent execution by the cycle-accurate
pipeline models.

The Pompia sample pipeline, which does perform cycle-accurate simulation,
executes at a rate of about 40 simulated cycles per real-world second at a
steady state system load of less than 10%. While 40 cycles/second is not
blazingly fast, as stated above (see: Software Architecture), I view the
flexibilty enabeld by Nebula's software architecture as a
more-than-worthwhile tradeoff. Also, consider that with the CPU utilization
so low, I am able to execute many simulations simulatenously without
saturating my CPU; this
comports well with the fact that much of microarchitecture research
requires large state-space searches, with many executions of the same
benchmarks under different parameters (e.g., cache capacity, cache
replacement algorithm, branch predictor).

Using the `executor.py` tool, I
was able to execute a large state space exploration on my laptop
comprised of approximately 6,200 simulations that ran for roughly 6,500
cycles apiece in just under 3 hours with `--max_cpu_utilization` set to 90
(so that I could continue to use my laptop for other tasks); that is a very
respectable aggregate simulation rate of roughly 3,700 cycles/second on a
consumer-grade laptop!

Finally, consider that I have so far made almost no effort to optimize the
simulator, choosing instead at this early stage to focus primarily on
correctness; future optimization efforts will doubtless increase the
execution speed of both Amanatsu and the cycle-accurate pipeline models.

# Instruction Implementation Tests

The correctness of the simulator's results is directly linked to the
correctness of the instruction implementations: if the instructions are
not correct, then the results generated by the simulator are unreliable.
This software package, therefore, also contains an instruction implementation
test harness, `test.py`.

An example execution would be elucidative:

    mkdir -p /tmp/nebula/test
    python3 ./test.py \
        --loop 5
        --insns addi slli c.addi16sp \
        -- \
        10000 \
        /opt/riscv/bin/riscv-unknown-elf-gcc
        /tmp/nebula/test

The `mkdir` command just creates a location for all the artifacts of
the test harness's execution. The `--loop` parameter tells the test
harness that the tests it executes are to be performed 5 times apiece;
if this parameter is omitted, the tests are performed once.
The `--insns` parameter gives the instructions whose implementations
are to be tested; if this parameter is omitted, all of the instruction
implementations are tested. Finally, the last three parameters tell:
the network port to use, the location of the RISC-V cross compiler,
and the location of the output directory, respectively.

The test harness creates a small assembly language program with
randomly generated inputs, and the expected correct response. For
instance, if the ADD instruction is being tested, and tne inputs to
it are 2 and 3, then the expected correct output is 5. If the result
returned by the Bergamot pipeline is different than 5, the test
harness will halt and print the assembly program, as well as the
expected result and the result returned by the Bergamot pipeline.

The problem causing the discrepancy may be either the simulator's
implementation of the instruction, or the test harness's expected
result. But if the two mismatch, that is a sign that further
investigation needs to be done to indentify the cause of the
discrepancy.

# Future Features

Presented in no particular order, here are some additional features that will
extend and enhance the simulator:

1. pipeline implementation with value prediction
1. pipeline implementation with out-of-order execution
1. Kubernetes deployment
1. perfect branch predictor
1. perfect value predictor
1. return address stack
1. accelerated `mmap`-based main memory implementation
1. implement new eviction policies (e.g., least frequently used) for SimpleCache and SimpleBTB
1. ARM instruction set support
1. MIPS instruction set support
1. x86_64 instruction set support
1. SPARC v9 instruction set support
1. sample Jupyter Notebook for fetching and processing data from MongoDB
1. ~~pipeline implementation with decoupled fetch engine~~
1. ~~multi-core support with cache sharing~~
1. ~~syscall proxying~~
1. ~~launch from binary's `_start` label rather than `main` label~~
1. ~~tool for cataloging, indexing, and retrieving simulator runs~~

That said, since this is a toolkit intended to facilitate microarchitecture
research, some of these, as my math textbooks used to say, "will be left as
an exercise" for researchers.

# Contact

I am available to consult on the Nebula framework's use, development and
deploymnt, and microprocessor simulation generally.

Email: john.haskins.jr@gmail.com |
LinkedIn: https://www.linkedin.com/in/john-haskins-jr-925235a1/