# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import itertools
import random

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )

class SimpleCache:
    def __init__(self, nsets, nways, nbytesperblock, evictionpolicy):
        assert 0 == (nsets & (nsets - 1)), 'nset ({}) must be a power of 2'.format(nsets)
        assert 0 == (nbytesperblock & (nbytesperblock - 1)), 'nbyte ({}) must be a power of 2'.format(nbytesperblock)
        self.nsets = nsets
        self.nways = nways
        self.nbytesperblock = nbytesperblock
        self.evictionpolicy = evictionpolicy
        self.sets = {}
        self.purge()
    def purge(self):
        self.sets = {
            x: [
                {
                    'tag': None,
                    'data': [0xff] * self.nbytesperblock,
                    'dirty': False,
                    'misc': {},
                } for _ in range(self.nways)
             ] for x in range(self.nsets)
        }
    def invalidate(self, **kwargs):
        if kwargs.get('misc'):
            _misc = kwargs.get('misc')
            self.sets = {
                x: [
                    (y if _misc != y.get('misc') else {
                        'tag': None,
                        'data': [0xff] * self.nbytesperblock,
                        'dirty': False,
                        'misc': {},
                    }) for y in self.sets[x]
                ] for x in self.sets.keys()
            }
    def tag(self, addr): return (addr >> (log2(self.nsets) + log2(self.nbytesperblock)))
    def setnum(self, addr): return (addr >> log2(self.nbytesperblock)) & ((1 << log2(self.nsets)) - 1)
    def waynum(self, addr, s):
        _way = list(filter(lambda w: s[w].get('tag') == self.tag(addr), range(self.nways)))
        if not len(_way): return None
        assert 1 == len(_way), 'Multiple tag matches among the ways?!?!? (@{:08x} {})'.format(addr, s)
        return _way.pop()
    def offset(self, addr): return (addr & ((1 << log2(self.nbytesperblock)) - 1))
    def fits(self, addr, nbytes):
        _offset = self.offset(addr)
        return (_offset + nbytes - 1) < self.nbytesperblock
    def blockaddr(self, addr):
        return (addr >> log2(self.nbytesperblock)) << log2(self.nbytesperblock)
    def victim(self, s):
        if 'random' == self.evictionpolicy:
            return random.choice(list(range(len(s))))
        if 'lru' == self.evictionpolicy:
            s.pop(-1)
            s.insert(0, {
                'tag': None,
                'data': [0xff] * self.nbytesperblock,
                'dirty': False,
                'misc': {},
            })
            return 0
        assert False, 'Unknown eviction policy: {}'.format(self.evictionpolicy)
    def peek(self, addr, nbytes):
        _offset = self.offset(addr)
        assert self.fits(addr, nbytes), 'request does not fit in block! ({:08x} {} {})'.format(addr, _offset, nbytes)
        _set = self.sets[self.setnum(addr)]
        _w = self.waynum(addr, _set)
        _retval = None
        if isinstance(_w, int):
            _retval = _set[_w].get('data')[_offset:(_offset + nbytes)]
            _set.insert(0, _set.pop(_w))
        return _retval
    def misc(self, addr, data=None):
        _set = self.sets[self.setnum(addr)]
        _w = self.waynum(addr, _set)
        _retval = None
        if isinstance(_w, int):
            if data: _set[_w].update({'misc': data})
            _retval = _set[_w].get('misc')
        return _retval
    def poke(self, addr, data):
        _offset = self.offset(addr)
        assert self.fits(addr, len(data)), 'request does not fit in block! ({:08x} {} {})'.format(addr, _offset, len(data))
        _set = self.sets[self.setnum(addr)]
        _w = self.waynum(addr, _set)
        _w = (_w if isinstance(_w, int) else self.victim(_set))
        _data = _set[_w].get('data')[:]
        _data = _data[:_offset] + data + _data[_offset + len(data):]
        _set[_w].update({
            'tag': self.tag(addr),
            'data': _data,
            'dirty': True,
            'misc': _set[_w].get('misc')
        })
