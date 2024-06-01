# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import itertools

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )
def offset(pagesize, addr): return (addr & (pagesize - 1))
def frame(pagesize, addr, coreid): return ((addr | (pagesize - 1)) ^ (pagesize - 1)) | coreid # NOTE: max # cores, therefore, is pagesize
def coreid(pagesize, frame): return frame & (pagesize - 1)

class SimpleMMU:
    BASE = 0x1000_0000
    def __init__(self, pagesize):
        assert 0 == (pagesize & (pagesize - 1)), 'pagesize must be a power of 2!'
        self.pagesize = pagesize
#        self.pageoffsetmask = self.pagesize - 1
#        self.pageoffsetbits = log2(self.pagesize)
        self.translations = {}
    def offset(self, addr): return offset(self.pagesize, addr)
    def frame(self, addr, coreid): return frame(self.pagesize, addr, coreid)
    def coreid(self, frame): return coreid(self.pagesize, frame)
#    def coreid(self, k): return (k >> self.pageoffsetbits)
    def translate(self, addr, coreid):
#        _k = (coreid, addr >> self.pageoffsetbits) # BLERG: tuples cannot be keys in JSON
#        _k = (coreid << self.pageoffsetbits) | (addr >> self.pageoffsetbits)
        _k = frame(self.pagesize, addr, coreid)
#        self.translations.update({_k: self.translations.get(_k, self.BASE + (len(self.translations.keys()) << self.pageoffsetbits))})
        self.translations.update({_k: self.translations.get(_k, self.BASE + (len(self.translations.keys()) << log2(self.pagesize)))})
        return self.translations.get(_k) | offset(self.pagesize, addr)
    def purge(self, coreid):
        self.translations = {k:v for k, v in self.translations.items() if coreid != self.coreid(k)}
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)