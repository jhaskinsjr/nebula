# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import mmap
import argparse
import itertools
import logging
import time
import subprocess
import itertools
import json

import elftools.elf.elffile

import service
import toolbox
import toolbox.stats
import simplemmu

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )

class SimpleMainMemory:
    DEFAULT = {
        'pagesize': 2**16,
        'filename': '/tmp/mainmem.raw',
        'capacity': 2**32,
        'peek_latency_in_cycles': 10**3,
        'v2p_latency_in_cycles': 10**2,
    }
    def __init__(self, name, launcher, s=None, **kwargs):
        self.name = name
        self.service = (service.Service(self.get('name'), self.get('coreid', -1), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.config = {
            'pagesize': kwargs.get('pagesize', self.DEFAULT.get('pagesize')),
            'filename': kwargs.get('filename', self.DEFAULT.get('filename')),
            'capacity': kwargs.get('capacity', self.DEFAULT.get('capacity')),
            'peek_latency_in_cycles': kwargs.get('peek_latency_in_cycles', self.DEFAULT.get('peek_latency_in_cycles')),
            'v2p_latency_in_cycles': kwargs.get('v2p_latency_in_cycles', self.DEFAULT.get('v2p_latency_in_cycles')),
        }
        self.pageoffsetmask = None
        self.pageoffsetbits = None
        self.mmu = None
        self.cycle = 0
        self.active = True
        self.running = False
        self.booted = False
        self.ack = True
        self.fd = None
        self.mm = None
        self.snapshots = None
        self.stats = toolbox.stats.CounterBank(self.get('coreid', -1), name)
    def boot(self):
        assert 0 == (self.config.get('pagesize') & (self.config.get('pagesize') - 1)), 'pagesize ({}) is not power of 2!'.format(self.config.get('pagesize'))
        self.pageoffsetmask = self.config.get('pagesize') - 1
        self.pageoffsetbits = log2(self.config.get('pagesize'))
        self.mmu = simplemmu.SimpleMMU(self.config.get('pagesize'))
        self.fd = os.open(self.config.get('filename'), os.O_RDWR|os.O_CREAT)
        os.ftruncate(self.get('fd'), self.config.get('capacity'))
        self.mm = mmap.mmap(self.fd, self.config.get('capacity'))
        self.update({'booted': True})
    def loadbin(self, coreid, start_symbol, sp, pc, binary, *args):
        logging.info('loadbin(): binary : {} ({})'.format(binary, type(binary)))
        logging.info('loadbin(): args   : {} ({})'.format(args, type(args)))
        logging.info('loadbin(): coreid : {} ({})'.format(coreid, type(coreid)))
        _start_pc = pc
        with open(binary, 'rb') as fp:
            elffile = elftools.elf.elffile.ELFFile(fp)
            for section in filter(lambda x: x.header.sh_addr, elffile.iter_sections()):
                if not section: continue
                _addr = pc + section.header.sh_addr
                logging.info('loadbin(): {} : 0x{:08x} ({})'.format(section.name, _addr, section.data_size))
                self.poke(_addr, section.data_size, section.data(), **{'coreid': coreid}) # FIXME: this assumes each section will be less than self.pagesize bytes
            _symbol_tables = [s for s in elffile.iter_sections() if isinstance(s, elftools.elf.elffile.SymbolTableSection)]
            _start = sum([list(filter(lambda s: start_symbol == s.name, tab.iter_symbols())) for tab in _symbol_tables], [])
            assert 0 < len(_start), 'No {} symbol!'.format(start_symbol)
            assert 2 > len(_start), 'More than one {} symbol?!?!?!?'.format(start_symbol)
            _start = next(iter(_start))
            _start_pc = pc + _start.entry.st_value
        # The value of the argc argument is the number of command line
        # arguments. The argv argument is a vector of C strings; its elements
        # are the individual command line argument strings. The file name of
        # the program being run is also included in the vector as the first
        # element; the value of argc counts this element. A null pointer
        # always follows the last element: argv[argc] is this null pointer.
        #
        # For the command ‘cat foo bar’, argc is 3 and argv has three
        # elements, "cat", "foo" and "bar". 
        #
        # https://www.gnu.org/software/libc/manual/html_node/Program-Arguments.html
        #
        # see also: https://refspecs.linuxbase.org/LSB_3.1.1/LSB-Core-generic/LSB-Core-generic/baselib---libc-start-main-.html
        _argc = len(args)      # binary name is argv[0]
        _args = list(map(lambda a: '{}\0'.format(a), args))
        _fp  = sp
        _fp += 8               # 8 bytes for argc
        _fp += 8 * (1 + _argc) # 8 bytes for each argv * plus 1 NULL pointer
        _addr = list(itertools.accumulate([8 + _fp] + list(map(lambda a: len(a), _args))))
        logging.info('loadbin(): argc : {}'.format(_argc))
        logging.info('loadbin(): len(_args) : {}'.format(sum(map(lambda a: len(a), _args))))
        for x, y in zip(_addr, _args):
            logging.info('loadbin(): @{:08x} : {} ({})'.format(x, y, len(y)))
        self.poke(sp, 8, _argc.to_bytes(8, 'little'), **{'coreid': coreid}) #argc
        for x, a in enumerate(_addr):
            self.poke(sp + (1+x)*8, 8, a.to_bytes(8, 'little'), **{'coreid': coreid}) # argv pointers
        self.poke(sp + (1+len(_addr))*8, 8, (0).to_bytes(8, 'little'), **{'coreid': coreid})
        self.poke(sp + (2+len(_addr))*8, 8, bytes(''.join(_args), 'ascii'), **{'coreid': coreid})
        return _start_pc
    def snapshot(self, data):
        logging.info('snapshot(): data   : {}'.format(data))
        _snapshot_filename = '{}.{:015}.snapshot'.format(self.get('config').get('filename'), data.get('instructions_committed'))
        subprocess.run('cp {} {}'.format(self.get('config').get('filename'), _snapshot_filename).split())
        _state = json.dumps({
            **data,
            **{
                'mmu': self.mmu.translations,
            },
        })
        logging.info('snapshot(): mmu    : {}'.format(self.mmu.translations))
        logging.info('snapshot(): _state : {}'.format(_state))
        fd = os.open(_snapshot_filename, os.O_RDWR | os.O_CREAT)
        os.lseek(fd, self.config.get('capacity'), os.SEEK_SET)
        os.write(fd, len(_state).to_bytes(8, 'little'))
        os.write(fd, bytes(_state, encoding='ascii'))
        os.fsync(fd)
        os.close(fd)
        logging.info('snapshot(): snapshot saved to {}'.format(_snapshot_filename))
        # FIXME: make snapshots read-only after creation
        return _snapshot_filename
    def restore(self, snapshot_filename):
        subprocess.run('cp {} {}'.format(snapshot_filename, self.get('config').get('filename')).split())
        subprocess.run('chmod u+w {}'.format(self.get('config').get('filename')).split())
        fd = os.open(snapshot_filename, os.O_RDONLY)
        os.lseek(fd, self.config.get('capacity'), os.SEEK_SET)
        _state_length = int.from_bytes(os.read(fd, 8), 'little')
        _retval = str(os.read(fd, _state_length), encoding='ascii')
        _retval = json.loads(_retval)
        _retval.update({'registers': {(k if '%pc' == k else int(k)):v for k, v in _retval.get('registers').items()}})
        _retval.update({'mmu': {int(x):y for x, y in _retval.get('mmu').items()}})
        self.mmu.translations = _retval.get('mmu')
        os.close(fd)
        for k, v in _retval.get('registers').items(): self.service.tx({'register': {
            'coreid': 0, # TODO: allow restore of multi-core snapshots
            'cmd': 'set',
            'name': k,
            'data': v,
        }})
        logging.info('SimpleMainMemory.restore(): _retval : {}'.format(_retval))
        return _retval
    def state(self):
        return {
            'cycle': self.get('cycle'),
            'service': self.get('name'),
            'coreid': self.get('coreid', -1),
        }
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def do_tick(self, results, events):
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.stats.get(self.state().get('coreid')).get(self.state().get('service'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _coreid, ev in map(lambda x: (x.get('coreid'), x.get('mem')), filter(lambda y: 'mem' in y.keys(), events)):
            _cmd = ev.get('cmd')
            _addr = ev.get('addr')
            _size = ev.get('size')
            _data = ev.get('data')
            _kwargs = {'coreid': _coreid, **({} if not ev.get('physical') else {'physical': ev.get('physical')})}
            if 'poke' == _cmd:
                self.poke(_addr, _size, _data, **_kwargs)
#                toolbox.report_stats(self.service, self.state(), 'histo', 'poke.size', _size)
                self.stats.refresh('histo', 'poke_size', _size)
            elif 'peek' == _cmd:
                self.service.tx({'result': {
                    'arrival': self.get('config').get('peek_latency_in_cycles') + self.get('cycle'),
                    'coreid': _coreid,
                    'mem': {
                        'addr': _addr,
                        'size': _size,
                        'data': self.peek(_addr, _size, **_kwargs),
                    }
                }})
#                toolbox.report_stats(self.service, self.state(), 'histo', 'peek.size', _size)
                self.stats.refresh('histo', 'peek_size', _size)
            elif _cmd in ['purge', 'invalidate']:
                pass # b/c these may be propogated down the cache hierarchy
            else:
                logging.fatal('ev : {}'.format(ev))
                assert False
        for _coreid, ev in map(lambda x: (x.get('coreid'), x.get('mmu')), filter(lambda y: 'mmu' in y.keys(), events)):
            _cmd = ev.get('cmd')
            _vaddr = ev.get('vaddr')
            if 'purge' == _cmd:
                self.mmu.purge(_coreid)
            elif 'v2p' == _cmd:
                _paddr = self.mmu.translate(_vaddr, _coreid)
                self.service.tx({'result': {
                    'arrival': self.get('config').get('v2p_latency_in_cycles') + self.get('cycle'),
                    'coreid': _coreid,
                    'mmu': {
                        'vaddr': _vaddr,
                        'frame': self.mmu.frame(_paddr),
                        'offset': self.mmu.offset(_paddr),
                    }
                }})
    def valid_access(self, addr, size):
        retval  = addr >= 0
        retval &= (addr + size) < self.get('config').get('capacity')
        return retval
    def do_poke(self, addr, data, **kwargs):
        # data : list of unsigned char, e.g., to make an integer, X, into a list
        # of N little-endian-formatted bytes -> list(X.to_bytes(N, 'little'))
        assert isinstance(kwargs.get('coreid'), int)
        _addr = (self.mmu.translate(addr, kwargs.get('coreid')) if not kwargs.get('physical') else addr)
        logging.debug('do_poke({:08x}, ..., {}) -> {:08x}'.format(addr, kwargs, _addr))
        try:
            self.mm[_addr:_addr+len(data)] = bytes(data) 
        except:
            pass # FIXME: Something other than ignoring the issue should happen here!
    def poke(self, addr, size, data, **kwargs):
        def accesses(addr, size, data, **kwargs):
            _pagesize = self.config.get('pagesize')
            if simplemmu.frame(_pagesize, addr) == simplemmu.frame(_pagesize, addr + size): return zip([addr], [data])
            _addrs = [addr]
            _sizes = [_pagesize - (addr - self.mmu.frame(addr))]
            _datas = [data[:_sizes[-1]]]
            while sum(_sizes) < len(data):
                _addrs += [self.mmu.frame(addr) + (len(_addrs) * _pagesize)]
                _x = _sizes[-1]
                _sizes += [min(_pagesize, size - sum(_sizes))]
                _datas += [data[_x:(_x + _sizes[-1])]]
            logging.debug('poke.accesses(): _addrs : ({}) {}'.format(kwargs.get('coreid'), '[{}]'.format(', '.join(map(lambda x: '{:08x}'.format(x), _addrs)))))
            return zip(_addrs, _datas)
        assert isinstance(kwargs.get('coreid'), int)
        logging.debug('poke({:08x}, {}, ..., {})'.format(addr, size, kwargs))
        if not self.valid_access(addr, size):
            logging.info('poke({:08}, {}, ..., {}): Access does not fit in memory boundaries!'.format(addr, size, kwargs))
            return
        for a, d in accesses(addr, len(data), data, **kwargs): self.do_poke(a, d, **kwargs)
    def do_peek(self, addr, size, **kwargs):
        # return : list of unsigned char, e.g., to make an 8-byte quadword from
        # a list, X, of N bytes -> int.from_bytes(X, 'little')
        assert isinstance(kwargs.get('coreid'), int)
        _addr = (self.mmu.translate(addr, kwargs.get('coreid')) if not kwargs.get('physical') else addr)
        logging.debug('do_peek({:08x}, {}, {}) -> {:08x}'.format(addr, size, kwargs, _addr))
        try:
            return list(self.mm[_addr:_addr + size])
        except:
            return []
    def peek(self, addr, size, **kwargs):
        def accesses(addr, size, **kwargs):
            _pagesize = self.config.get('pagesize')
            if simplemmu.frame(_pagesize, addr) == simplemmu.frame(_pagesize, addr + size): return zip([addr], [size])
            _addrs = [addr]
            _sizes = [_pagesize - (addr - self.mmu.frame(addr))]
            while sum(_sizes) < size:
                _addrs += [self.mmu.frame(addr) + (len(_addrs) * _pagesize)]
                _sizes += [min(_pagesize, size - sum(_sizes))]
            return zip(_addrs, _sizes)
        assert isinstance(kwargs.get('coreid'), int)
        logging.debug('peek({:08x}, {}, ..., {})'.format(addr, size, kwargs))
        if not self.valid_access(addr, size):
            logging.info('peek({:08}, {}, ..., {}): Access does not fit in memory boundaries!'.format(addr, size, kwargs))
            return []
        return sum([self.do_peek(a, s, **kwargs) for a, s in accesses(addr, size, **kwargs)], [])


if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Main Memory')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--pagesize', type=int, dest='pagesize', default=2**16, help='MMU page size in bytes')
    parser.add_argument('--filename', type=str, dest='filename', default='/tmp/mainmem.raw', help='file to hold main memory')
    parser.add_argument('--capacity', type=int, dest='capacity', default=2**32, help='size (in bytes) of main memory file')
    parser.add_argument('--peek_latency_in_cycles', type=int, dest='peek_latency_in_cycles', default=10**3, help='# of cycles to return peek result')
    parser.add_argument('--v2p_latency_in_cycles', type=int, dest='v2p_latency_in_cycles', default=10**2, help='# of cycles to return MMU result')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
    args = parser.parse_args()
    assert not os.path.isfile(args.log), '--log must point to directory, not file'
    while not os.path.isdir(args.log):
        try:
            os.makedirs(args.log, exist_ok=True)
        except:
            time.sleep(0.1)
    logging.basicConfig(
        filename=os.path.join(args.log, '{}.log'.format(os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = SimpleMainMemory('mainmem', _launcher, **{
        'pagesize': args.pagesize,
        'filename': args.filename,
        'capacity': args.capacity,
        'peek_latency_in_cycles': args.peek_latency_in_cycles,
        'v2p_latency_in_cycles': args.v2p_latency_in_cycles,
    })
    while state.get('active'):
        state.update({'ack': True})
        msg = state.service.rx()
#        state.service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif 'reset' == k:
                _coreid = v.get('coreid')
                logging.info('@{:15} : {}'.format(state.get('cycle'), msg))
                if state.get('booted'):
                    logging.info('@{:15} : state.mmu.translations : {}'.format(state.get('cycle'), state.mmu.get('translations')))
                    _pagesize = state.get('config').get('pagesize')
                    for f in state.mmu.pframes(_coreid): state.poke(f, _pagesize, [0] * _pagesize, **{'coreid': _coreid, 'physical': True})
                    state.mmu.purge(_coreid)
            elif {'text': 'run'} == {k: v}:
                logging.info('state.config : {}'.format(state.get('config')))
                if not state.get('booted'): state.boot()
                state.update({'running': True})
                state.update({'ack': False})
                state.service.tx({'info': 'state.config : {}'.format(state.get('config'))})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if v.get('service') not in [state.get('name'), 'all', 'mmu']: continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys() or 'all' == v.get('service'), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'loadbin' == k:
                _coreid = v.get('coreid')
                _start_symbol = v.get('start_symbol')
                _sp = v.get('sp')
                _pc = v.get('pc')
                _binary = v.get('binary')
                _args = v.get('args')
                if not state.get('booted'): state.boot()
                state.mmu.purge(_coreid)
                logging.info('@{:15} : state.mmu.translations : {}'.format(state.get('cycle'), state.mmu.get('translations')))
                state.loadbin(_coreid, _start_symbol, _sp, _pc, _binary, *_args)
            elif 'restore' == k:
                _snapshot_filename = v.get('snapshot_filename')
                if not state.get('booted'): state.boot()
                state.restore(_snapshot_filename)
                state.service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'snapshots' == k:
                state.update({'snapshots': v})
            elif 'tick' == k:
                logging.debug('tick - v : {}'.format(v))
                state.update({'cycle': v.get('cycle')})
                if v.get('snapshot'):
                    _data = v.get('snapshot').get('data')
                    state.snapshot(_data)
                _results = v.get('results')
                _events = v.get('events')
                state.do_tick(_results, _events)
        if state.get('ack') and state.get('running'): state.service.tx({'ack': {'cycle': state.get('cycle'), 'msg': msg}})
    state.get('mm').flush()
    state.get('mm').close()
    os.close(state.get('fd'))
    logging.info('state.mmu.translations : {}'.format(json.dumps(state.get('mmu').get('translations'), indent=4)))