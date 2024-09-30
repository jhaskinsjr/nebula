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

## Cycle-accurate Sample Pipeline Performance

The [Tangelo](../pipelines/tangelo/README.md) sample pipeline, which
*does* perform cycle-accurate simulation, executes at a rate of about 290
simulated cycles per real-world second at a steady state system load of
around 31%. While 290 cycles/second is not blazingly fast, my initial
primary objective with Nebula was to develop the concept of cycle-accurate
simulators build using modern microservices software architecture
(see: [Software Architecture](./Software_Architecture.md)). And since
premature optimization runs contrary to any engineering endeavor,
especially exploratory endeavors where novel concepts and architectures
are applied in novel ways in novel domains. Accordingly, I view the
flexibilty enabled by Nebula's software architecture as a
more-than-worthwhile tradeoff.

As the Nebula framework matured, I began work on improving performance
with the [Tangerine](../pipelines/tangerine/README.md) sample pipeline
as the result. Whereas Tangelo utilizes a per-component microservices
granularity, Tangerine models the same pipeline logic, but with per-core
microservices granularity. The per-component and per-core microservices
granularity levels explained in detail in
[Software Architecture](./Software_Architecture.md), but for now it is
enough to say that per-core granularity delivers much greater performance
than per-component, because it requires much less interprocess
communication. Consider that Tangerine executes as a rate of 866
simulated cycles per real-workd second, roughly 3 times faster than
Tangelo, at a steady state system load of slightly less than 30%.
Again: Tangerine achieves 3 times the simulation rate with **lower
CPU utilization**!

Also, consider that with the CPU utilization so low, I am able to execute
many simulations simulatenously without saturating my CPU; this comports
well with the fact that much of microarchitecture research requires large
state-space searches, with many executions of the same benchmarks under
different parameters (e.g., cache capacity, cache replacement algorithm,
branch predictor). Using the `executor.py` tool
(see: [Large-Scale Simulations](./Large-Scale_Studies.md)), I executed a
large state space exploration on my laptop comprised of 256 simulations
(with different configurations of the Tangerine pipeline model) that ran
for 10,000s of cycles apiece in a little less than 3 hours with CPU
utilization from Nebula processes capped at 90% (so that I could continue
to use my laptop for other work). The result was a very respectable
aggregate simulation rate of 1,300 simulated cycles per real-world second
on a consumer-grade laptop!

## Effect of SMT

Disabling SMT
(see: https://serverfault.com/questions/235825/disable-hyperthreading-from-within-linux-no-access-to-bios)
made no significant difference in Nebula performance.

## Effect of `tmpfs`

I found on my laptop that using a `tmpfs`
(see: https://www.kernel.org/doc/html/latest/filesystems/tmpfs.html)
RAM-based file system for storing simulation artifacts (e.g.,
`stats.json`, `mainmem.raw`, `launcher.py.log`) yielded a slight
performance boost.