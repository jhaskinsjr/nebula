# Future Features

Presented in no particular order, below are some additional features that will
extend and enhance the simulator. (Once-future features that have already been
implemented have been struck through.)

1. superscalar out-of-order pipeline implementation (code name: Yuzu)
1. retool per-core execution to leverage Python's `threading` module
1. per-core cycle count
1. cache snooping
1. pipeline implementation with value prediction
1. perfect branch predictor
1. perfect value predictor
1. return address stack
1. implement new eviction policies (e.g., least frequently used) for SimpleCache and SimpleBTB
1. Kubernetes deployment
1. ARM instruction set support
1. MIPS instruction set support
1. x86_64 instruction set support
1. SPARC v9 instruction set support
1. ~~"component'ized" Tangelo reimplementation (code name: Tangerine)~~
1. ~~"component'ized" Bergamot reimplementation (code name: Etrog)~~
1. ~~MMU service~~
1. ~~shared caches~~
1. ~~accelerated `mmap`-based main memory implementation~~
1. ~~sample Jupyter Notebook for fetching and processing data from MongoDB~~
1. ~~pipeline implementation with decoupled fetch engine~~
1. ~~multi-core support with cache sharing~~
1. ~~syscall proxying~~
1. ~~launch from binary's `_start` label rather than `main` label~~
1. ~~tool for cataloging, indexing, and retrieving simulator runs~~

That said, since this is a toolkit intended to facilitate microarchitecture
research, some of these, as my math textbooks used to say, "will be left as
an exercise" for researchers.