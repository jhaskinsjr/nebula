# Simulation Speed

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