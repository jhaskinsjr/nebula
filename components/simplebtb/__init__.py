# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

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
    def __init__(self, nentries, nbytesperentry, evictionpolicy):
        self.nentries = nentries
        self.nbytesperentry = nbytesperentry
        self.evictionpolicy = evictionpolicy
        self.entries = [{
            'pc': None,
            'entry': BTBEntry(0),
        } for _ in range(self.nentries)]
    def waynum(self, pc):
        _way = list(filter(lambda x: pc == x.get('pc'), self.entries))
        assert len(_way) < 2, 'Multiple matching blocks?!?\n\t{}\n\t{}'.format(_way, self.entries)
        return (self.entries.index(_way.pop()) if len(_way) else None)
    def victim(self):
        if 'random' == self.evictionpolicy:
            return random.choice(list(range(self.nentries)))
        if 'lru' == self.evictionpolicy:
            self.entries.pop(-1)
            self.entries.insert(0, {
                'pc': None,
                'entry': BTBEntry(0),
            })
            return 0
        assert False, 'Unknown eviction policy: {}'.format(self.evictionpolicy)
    def poke(self, pc, next_pc):
        if isinstance(self.waynum(pc), int): return
        self.entries[self.victim()] = {
            'pc': pc,
            'entry': BTBEntry(next_pc)
        }
    def peek(self, pc):
        _w = self.waynum(pc)
        return (self.entries[_w].get('entry') if isinstance(_w, int) else None)
    def update(self, next_pc, data):
        _w = list(filter(lambda x: next_pc == x.get('entry').addr, self.entries))
        if not len(_w): return
        _w = self.entries.index(_w.pop())
        # NOTE: It's theoretically possible, but unlikely, that more than one
        # BTB entry will have the same next_pc. I suppose I could extend both,
        # but not dealing with that now... for now, just update the 0th entry
        _entry = self.entries[_w].get('entry')
        _entry.data.extend(data)
        _entry.addr += len(data)
        if len(_entry.data) == self.nbytesperentry: _entry.addr = None
    def evict(self, pc):
        _w = self.waynum(pc)
        if isinstance(_w, int):
            self.entries[_w] = {
                'pc': None,
                'entry': BTBEntry(0),
            }