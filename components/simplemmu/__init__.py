# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import itertools

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )

class SimpleMMU:
    BASE = 0x1000_0000
    def __init__(self, pagesize):
        assert 0 == (pagesize & (pagesize - 1)), 'pagesize must be a power of 2!'
        self.pagesize = pagesize
        self.pageoffsetmask = self.pagesize - 1
        self.pageoffsetbits = log2(self.pagesize)
        self.translations = {}
    def translate(self, addr, coreid):
#        _k = (coreid, addr >> self.pageoffsetbits) # BLERG: tuples cannot be keys in JSON
        _k = (coreid << self.pageoffsetbits) | (addr >> self.pageoffsetbits)
        self.translations.update({_k: self.translations.get(_k, self.BASE + (len(self.translations.keys()) << self.pageoffsetbits))})
        return self.translations.get(_k) | (addr & self.pageoffsetmask)
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)