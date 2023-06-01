# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import sys
import argparse
import itertools
import logging
import time
import subprocess

import elftools.elf.elffile

import service
import toolbox

class SimpleMainMemory:
    def __init__(self, name, launcher, s=None):
        self.name = name
        self.service = (service.Service(self.get('name'), launcher.get('host'), launcher.get('port')) if not s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.fd = None
        self.config = {
            'filename': None,
            'capacity': None,
            'peek_latency_in_cycles': None,
        }
    def boot(self):
        self.fd = os.open(self.get('config').get('filename'), os.O_RDWR|os.O_CREAT)
        os.ftruncate(self.get('fd'), self.get('config').get('capacity'))
    def loadbin(self, start_symbol, sp, pc, binary, *args):
        logging.info('loadbin(): binary : {} ({})'.format(binary, type(binary)))
        logging.info('loadbin(): args   : {} ({})'.format(args, type(args)))
        _start_pc = pc
        with open(binary, 'rb') as fp:
            elffile = elftools.elf.elffile.ELFFile(fp)
            for section in filter(lambda x: x.header.sh_addr, elffile.iter_sections()):
                if not section: continue
                _addr = pc + section.header.sh_addr
                logging.info('{} : 0x{:08x} ({})'.format(section.name, _addr, section.data_size))
                os.lseek(self.get('fd'), _addr, os.SEEK_SET)
                os.write(self.get('fd'), section.data())
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
        os.lseek(self.get('fd'), sp, os.SEEK_SET)
        os.write(self.get('fd'), _argc.to_bytes(8, 'little'))       # argc
        for a in _addr:                                 # argv pointers
            os.write(self.get('fd'), a.to_bytes(8, 'little'))
        os.lseek(self.get('fd'), 8, os.SEEK_CUR)                    # NULL pointer
        os.write(self.get('fd'), bytes(''.join(_args), 'ascii'))    # argv data
        return _start_pc
    def snapshot(self, addr, data):
        _snapshot_filename = '{}.{:015}.snapshot'.format(self.get('config').get('filename'), data.get('instructions_committed'))
        subprocess.run('cp {} {}'.format(self.get('config').get('filename'), _snapshot_filename).split())
        fd = os.open(_snapshot_filename, os.O_RDWR | os.O_CREAT)
        os.lseek(fd, addr.get('cycle'), os.SEEK_SET)
        os.write(fd, (1 + data.get('cycle')).to_bytes(8, 'little'))
        os.lseek(fd, addr.get('instructions_committed'), os.SEEK_SET)
        os.write(fd, data.get('instructions_committed').to_bytes(8, 'little'))
        os.lseek(fd, addr.get('cmdline_length'), os.SEEK_SET)
        os.write(fd, len(data.get('cmdline')).to_bytes(8, 'little'))
        os.lseek(fd, addr.get('cmdline'), os.SEEK_SET)
        os.write(fd, bytes(data.get('cmdline'), 'ascii'))
        os.fsync(fd)
        os.close(fd)
        # FIXME: make snapshots read-only after creation
        return _snapshot_filename
    def restore(self, snapshot_filename, addr):
        subprocess.run('cp {} {}'.format(snapshot_filename, self.get('config').get('filename')).split())
        subprocess.run('chmod u+w {}'.format(self.get('config').get('filename')).split())
    def state(self):
        return {
            'cycle': self.get('cycle'),
            'service': self.get('name'),
        }
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def do_tick(self, results, events):
        for ev in filter(lambda x: x, map(lambda y: y.get('mem'), events)):
            _cmd = ev.get('cmd')
            _addr = ev.get('addr')
            _size = ev.get('size')
            _data = ev.get('data')
            if 'poke' == _cmd:
                self.poke(_addr, _size, _data)
                toolbox.report_stats(self.service, self.state(), 'histo', 'poke.size', _size)
            elif 'peek' == _cmd:
                self.service.tx({'result': {
                    'arrival': self.get('config').get('peek_latency_in_cycles') + self.get('cycle'),
                    'mem': {
                        'addr': _addr,
                        'size': _size,
                        'data': self.peek(_addr, _size),
                    }
                }})
                toolbox.report_stats(self.service, self.state(), 'histo', 'peek.size', _size)
            else:
                logging.fatal('ev : {}'.format(ev))
                assert False
    def poke(self, addr, size, data):
        # data : list of unsigned char, e.g., to make an integer, X, into a list
        # of N little-endian-formatted bytes -> list(X.to_bytes(N, 'little'))
        _fd = self.get('fd')
        try:
            os.lseek(_fd, addr, os.SEEK_SET)
            os.write(_fd, bytes(data))
        except:
            pass
#        os.write(_fd, data.to_bytes(size, 'little'))
    def peek(self, addr, size):
        # return : list of unsigned char, e.g., to make an 8-byte quadword from
        # a list, X, of N bytes -> int.from_bytes(X, 'little')
        _fd = self.get('fd')
        try:
            os.lseek(_fd, addr, os.SEEK_SET)
            return list(os.read(_fd, size))
        except:
            return []


if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Main Memory')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
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
    state = SimpleMainMemory('mainmem', _launcher)
    while state.get('active'):
        state.update({'ack': True})
        msg = state.service.rx()
#        state.service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif {'text': 'run'} == {k: v}:
                state.boot()
                state.update({'running': True})
                state.update({'ack': False})
                state.service.tx({'info': 'state.config : {}'.format(state.get('config'))})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('name') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'loadbin' == k:
                _start_symbol = v.get('start_symbol')
                _sp = v.get('sp')
                _pc = v.get('pc')
                _binary = v.get('binary')
                _args = v.get('args')
                state.boot()
                state.loadbin(_start_symbol, _sp, _pc, _binary, *_args)
            elif 'restore' == k:
                _snapshot_filename = v.get('snapshot_filename')
                _addr = v.get('addr')
                state.boot()
                state.restore(_snapshot_filename, _addr)
                state.service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                if v.get('snapshot'):
                    _addr = v.get('snapshot').get('addr')
                    _data = v.get('snapshot').get('data')
                    state.snapshot(_addr, _data)
                _results = v.get('results')
                _events = v.get('events')
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                state.service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): state.service.tx({'ack': {'cycle': state.get('cycle')}})
    os.close(state.get('fd'))