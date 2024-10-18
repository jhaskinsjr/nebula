# Sample Binaries

The sample binaries...

* examples/bin/sum
* examples/bin/sort
* examples/bin/sieve
* examples/bin/negate
* examples/bin/puts
* examples/bin/cat
* examples/bin/3sat
* examples/bin/gzip
* examples/bin/gunzip
* examples/bin/zcat
* examples/bin/sizeof
* examples/bin/dry2
* examples/bin/dry2o
* examples/bin/dry2nr

were created using the RISC-V
cross compiler at https://github.com/riscv-collab/riscv-gnu-toolchain,
following the directions under the "Installation (Newlib)" section; see:
https://github.com/riscv-collab/riscv-gnu-toolchain#installation-newlib.
Consider, for instance, the source for the sum program:

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

### Outside benchmarks

The gzip source was downloaded from
https://ftp.gnu.org/gnu/gzip/gzip-1.2.4.tar.gz, and built with
slight modifications according to a build recipe chronicled
[here](../examples/src/gzip-1.2.4/NEBULA).

Unlike the other sample programs, gzip is not a mere toy, but,
rather, a *real* benchmark that does *real* work. I have used it successfully
to compress my `.bash_history` file from about 375 KB down to about 15 KB
with the [Jabara](../pipelines/jabara/README.md) sample model; to wit:

    cd ${HOME}/src/nebula/pipelines/jabara ; \
    LOGDIR=/tmp/log/$( basename $( pwd ) ) ; \
    mkdir -p ${LOGDIR} ; \
    rm -f ${LOGDIR}/* ; \
    cp -f ${HOME}/.bash_history /tmp/.bash_history ; \
    time ( \
        python3 ../../launcher.py \
            --log ${LOGDIR} \
            --service ../../toolbox/stats.py:localhost:22:-1:-1 \
            --config \
                stats:output_filename:${LOGDIR}/stats.json \
                mainmem:filename:${LOGDIR}/mainmem.raw \
                mainmem:capacity:$(( 2**32 )) \
            -- \
            $(( 1000 + ${RANDOM} )) \
            localhost.nebula \
            /home/john/src/nebula/examples/bin/gzip /tmp/.bash_history \
    )

On my laptop the simulation, executed 71.2 million instructions at a
rate of about 26,000 instructions/second, and completed in a bit less than
46 minutes. As expected, this emitted nothing to my terminal, but wrote
`/tmp/.bash_history.gz` and deleted `/tmp/.bash_history`.

And uncompressing...

    cd ${HOME}/src/nebula/pipelines/jabara ; \
    LOGDIR=/tmp/log/$( basename $( pwd ) ) ; \
    mkdir -p ${LOGDIR} ; \
    rm -f ${LOGDIR}/* ; \
    time ( \
        python3 ../../launcher.py \
            --log ${LOGDIR} \
            --service ../../toolbox/stats.py:localhost:22:-1:-1 \
            --config \
                stats:output_filename:${LOGDIR}/stats.json \
                mainmem:filename:${LOGDIR}/mainmem.raw \
                mainmem:capacity:$(( 2**32 )) \
            -- \
            $(( 1000 + ${RANDOM} )) \
            localhost.nebula \
            /home/john/src/nebula/examples/bin/gunzip /tmp/.bash_history.gz \
    )

...executed 12 million instructions at about 25,000 instructions/second,
and completed in a little more than 8 minutes, writing `/tmp/.bash_history` and
deleting `/tmp/.bash_history.gz`.