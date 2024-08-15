# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import itertools

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )
def offset(pagesize, addr): return (addr & (pagesize - 1))
def frame(pagesize, addr): return ((addr | (pagesize - 1)) ^ (pagesize - 1))

class SimpleMMU:
    BASE = 0x1000_0000
    def __init__(self, pagesize):
        assert 0 == (pagesize & (pagesize - 1)), 'pagesize must be a power of 2!'
        self.pagesize = pagesize
        self.translations = {}
    def offset(self, addr): return offset(self.pagesize, addr)
    def frame(self, addr): return frame(self.pagesize, addr)
    def pframes(self, coreid): return list(map(lambda y: y.get('frame'), filter(lambda x: coreid == x.get('coreid'), self.translations.values())))
    def translate(self, addr, coreid):
        _k = frame(self.pagesize, addr) | coreid
        self.translations.update({_k: self.translations.get(_k, {
#            'frame': self.BASE + (len(self.translations.keys()) << log2(self.pagesize)),
            'frame': next(filter(
                lambda x: x not in map(lambda y: y.get('frame'), self.translations.values()),
                map(lambda z: self.BASE + (z << log2(self.pagesize)), range(len(self.translations.keys())))
            ), self.BASE + (len(self.translations.keys()) << log2(self.pagesize))),
            'coreid': coreid,
        })})
        assert len(list(map(lambda x: x.get('frame'), self.translations.values()))) == len(set(map(lambda x: x.get('frame'), self.translations.values()))), 'Shared physical frame! {}'.format(self.translations)
        return self.translations.get(_k).get('frame') | offset(self.pagesize, addr)
    def purge(self, coreid):
        self.translations = {k:v for k, v in self.translations.items() if coreid != v.get('coreid')}
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)