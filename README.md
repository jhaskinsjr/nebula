# Nebula: The Cloud-Native Microarchitecture Simulation Framework!

Nebula is a framework for
developing cycle-accurate microprocessor simulators comprised of multiple,
independent processes that communicate over a network.

The framework includes Python libraries for decoding and executing
statically linked RISC-V binaries, as well as several sample pipeline
implementations built using the framework.


# Quick Start

The following instructions should help you to get a simulation up and
running with minimal effort. For more detailed analysis of Nebula, how
it works, its sample pipeline implementations, software architecture,
design philosophy, using it for running multicore simulations,
running distributed simulations, etc., refer to the
[Documentation](#documentation) below.

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
        --service ../../toolbox/stats.py:localhost:22:-1 implementation/mainmem.py:localhost:22:-1 \
        --config stats:output_filename:/tmp/pompia/sum/stats.json \
        mainmem:filename:/tmp/pompia/sum/mainmem.raw \
        mainmem:capacity:$(( 2**32 )) \
        --max_instructions $(( 10**5 )) \
        -- \
        12345 \
        localhost.nebula \
        ../../examples/bin/sum 2 3 5 7 11 13

The "python3" command executes the Nebula launcher (launcher.py),
which begins by opening a socket and accepting connections on port 12345,
executing the script localhost.nebula, and loading the binary
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


# Documentation

There is much more to Nebula than what is covered in the [Quick Start](#quick-start) guide
(supra). Consider, for instance, that the Nebula framework uses multiple,
loosely coupled, independent processes to effect cycle-accurate simulations;
see: [Software Architecture](Documentation/Software_Architecture.md).
Consider
further that these independent processes need not all execute on the same
node; see: [Distributed Simulation](Documentation/Distributed_Simulation.md).
Consider further still that the Nebula framework also includes tools to
facilitate large-scale studies via MongoDB, Pandas, and Jupyter Notebooks ; see:
[Large-Scale Studies](Documentation/Large-Scale_Studies.md). Information
about these topics and much more are covered in the links below.

1. [Software Architecture](Documentation/Software_Architecture.md)
1. [Sample Pipelines](Documentation/Sample_Pipelines.md)
1. [JSON Output](Documentation/JSON_Output.md)
1. [Watchdog Tool](Documentation/Watchdog.md)
1. [Snapshots](Documentation/Snapshots.md)
1. [Simulator Scripts](Documentation/Simulator_Scripts.md)
1. [Distributed Simulation](Documentation/Distributed_Simulation.md)
1. [Multicore Simulation](Documentation/Multicore_Simulation.md)
1. [Sample Binaries](Documentation/Sample_Binaries.md)
1. [Large-Scale Studies](Documentation/Large-Scale_Studies.md)
1. [Simulation Speed](Documentation/Simulation_Speed.md)
1. [Instruction Implementation Tests](Documentation/Instruction_Implementation_Tests.md)
1. [Future Features](Documentation/Future_Features.md)


# Latest Version

The most recent tagged release is `v1.1.0` (as of 20240205), which builds
upon `v1.0.0` by adding:

* *new* [Jabara](pipelines/jabara/README.md) functional execution model
* faster [Amanatsu](pipelines/amanatsu/README.md) functional execution model
* faster `SimpleRegisterFile` (see: [components/simpleregfile/__init__.py](components/simpleregfile/__init__.py))
* faster `SimpleMainMemory` (see: [components/simplemainmem/__init__.py](components/simplemainmem/__init__.py))
* faster LOAD/STORE instruction execution in [Shangjuan](pipelines/shangjuan/README.md) cycle-accurate model
* documentation updates and clarifications
* miscellaneous bug fixes

# Contact

I am available to consult on the Nebula framework's use, development and
deploymnt, and microprocessor simulation generally.

Email: john.haskins.jr@gmail.com |
LinkedIn: https://www.linkedin.com/in/john-haskins-jr-925235a1/