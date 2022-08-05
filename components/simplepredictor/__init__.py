import itertools

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )
def saturating_inc(x, a): return (x if a == x else 1 + x)
def saturating_dec(x, a): return (x if a == x else x - 1) 

class SimplePredictor:
    def __init__(self, nentries):
        assert 0 < nentries, 'nentries ({}) must be a positive power of 2'.format(nentries)
        assert 0 == (nentries & (nentries - 1)), 'nentries ({}) must be a power of 2'.format(nentries)
        self.nentries = nentries
        self.entries = {x:0 for x in range(self.nentries)}
    def poke(self, addr, taken):
        _k = addr & ((1 << log2(self.nentries)) - 1)
        _v = self.entries.get(_k)
        self.entries.update({_k: (saturating_inc(_v, 3) if taken else saturating_dec(_v, 0))})
    def peek(self, addr):
        _k = addr & ((1 << log2(self.nentries)) - 1)
        return 1 < self.entries.get(_k)