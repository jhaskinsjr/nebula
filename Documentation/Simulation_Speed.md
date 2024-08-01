# Simulation Speed

On my laptop, a Lenovo ThinkPad with 32 GB of RAM and an Intel Core
i7-8565U, running Ubuntu MATE 22.04, [Jabara](../pipelines/jabara/README.md)
executes at a rate of approximately 33,500 instructions/second; and
[Amanatsu](../pipelines/amanatsu/README.md) executes at a rate of
approximately 10,200 instructions/second. However, neither performs
cycle-accurate simulation; rather, they execute instructions in a
tight loop, updating state (main memory and the register file) as rapidly as
possible. This is what makes Jabara and Amanatsu ideal for creating
simulation snapshots for subsequent execution by the cycle-accurate pipeline
models.

The Pompia sample pipeline, which *does* perform cycle-accurate simulation,
executes at a rate of about 360 simulated cycles per real-world second at a
steady state system load of less than 30%. While 360 cycles/second is not
blazingly fast (see: [Software Architecture](./Software_Architecture.md)), my
primary objective with Nebula is to develop the concept of cycle-accurate
simulators build using modern microservices software architecture. Premature
optimization runs contrary to any engineering endeavor, especially
exploratory endeavors where novel concepts and architectures are applied in
novel ways in novel domains. Accordingly, I view the flexibilty enabled by
Nebula's software architecture as a more-than-worthwhile tradeoff.

Also, consider that with the CPU utilization
so low, I am able to execute many simulations simulatenously without
saturating my CPU; this comports well with the fact that much of
microarchitecture research requires large state-space searches, with many
executions of the same benchmarks under different parameters (e.g., cache
capacity, cache replacement algorithm, branch predictor).

Using the `executor.py` tool
(see: [Large-Scale Simulations](./Large-Scale_Studies.md)), I executed a
large state space exploration on my laptop comprised of 72 simulations
(with different configurations of the
[Pompia](../pipelines/pompia/README.md),
[Rangpur](../pipelines/rangpur/README.md), and
[Shangjuan](../pipelines/shangjuan/README.md) pipeline models) that ran for
10,000s of cycles apiece in about 40 minutes with CPU utilization from
Nebula processes capped at 90% (so that I could continue to use my laptop
for other work). The result was a very respectable aggregate simulation
rate of over 500 simulated cycles per real-world second on a
consumer-grade laptop!

## Effect of SMT

Disabling SMT
(see: https://serverfault.com/questions/235825/disable-hyperthreading-from-within-linux-no-access-to-bios)
made no significant difference in Nebula performance.

## Effect of `tmpfs`

I found on my laptop that using a `tmpfs`
(see: https://www.kernel.org/doc/html/latest/filesystems/tmpfs.html)
RAM-based file system for storing simulation artifacts (e.g.,
`stats.json`, `mainmem.raw`) yielded a slight performance boost. Since my
laptop has 32 GB of RAM, I created an 8 GB `tmpfs` file system.

## Performance-oriented Implementation

Now that I have developed and matured the concept of microservices-oriented
cycle-accurate simulation, if I had to implement Nebula for production
deployment, I would likely: (1) package each core's components inside a
single process and reserve interprocess communication for shared resources
like caches and main memory; and (2) use a compiled language (e.g., C).