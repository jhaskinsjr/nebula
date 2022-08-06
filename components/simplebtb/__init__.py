import random

class BTBEntry:
    def __init__(self, next_pc, counter_nbits=2):
        self.next_pc = next_pc
        self.addr = next_pc
        self.counter = (1 << (counter_nbits - 1)) - 1 # intially weakly not-taken
        self.counter_max = (1 << counter_nbits) - 1
        self.data = []
    def inc(self): self.counter += (1 if self.counter < self.counter_max else 0)
    def dec(self): self.counter -= (1 if self.counter > 0 else 1)
    def __repr__(self):
        return '[{} ; {} ; 0b{:04b}; {}]'.format(list((self.next_pc).to_bytes(8, 'little')), self.addr, self.counter, self.data)
class SimpleBTB:
    def __init__(self, nentries, nbytesperentry):
        self.nentries = nentries
        self.nbytesperentry = nbytesperentry
        self.entries = {}
    def poke(self, pc, next_pc):
        if not pc in self.entries.keys():
            if len(self.entries.keys()) == self.nentries:
                _victim = random.choice(list(self.entries.keys())) # HACK: random replacement good enough for now
                self.entries.pop(_victim)
            self.entries.update({pc: BTBEntry(next_pc)})
    def peek(self, pc):
        if not pc in self.entries.keys(): return None
        return self.entries.get(pc)
    def update(self, next_pc, data):
        _results = list(filter(lambda k: next_pc == self.entries.get(k).addr, self.entries.keys()))
        if not len(_results): return
        # NOTE: It's theoretically possible, but unlikely, that more than one
        # BTB entry will have the same next_pc. I suppose I could extend both,
        # but not dealing with that now... for now, just update the 0th entry
        _k = _results.pop(0)
        self.entries.get(_k).data.extend(data)
        self.entries.get(_k).addr += len(data)
        if len(self.entries.get(_k).data) == self.nbytesperentry: self.entries.get(_k).addr = None
    def evict(self, pc):
        if pc in self.entries.keys(): self.entries.pop(pc)