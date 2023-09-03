# JSON Output

Consider the following example stats.json output, gathered by executing
the 3SAT solver sample binary on the Pompia sample pipeline:

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