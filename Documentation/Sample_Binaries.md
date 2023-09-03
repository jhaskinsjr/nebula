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