# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

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
            'main_memory_filename': None,
            'main_memory_capacity': None,
            'peek_latency_in_cycles': None,
        }
#        self.fd = os.open(self.get('config').get('main_memory_filename'), os.O_RDWR|os.O_CREAT)
#        os.ftruncate(self.get('fd'), self.get('config').get('main_memory_capacity'))
    def boot(self):
        self.fd = os.open(self.get('config').get('main_memory_filename'), os.O_RDWR|os.O_CREAT)
        os.ftruncate(self.get('fd'), self.get('config').get('main_memory_capacity'))
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
#                state.update({'fd': os.open(state.get('config').get('main_memory_filename'), os.O_RDWR|os.O_CREAT)})
#                os.ftruncate(state.get('fd'), state.get('config').get('main_memory_capacity'))
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
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = v.get('results')
                _events = v.get('events')
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                state.service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): state.service.tx({'ack': {'cycle': state.get('cycle')}})
    os.close(state.get('fd'))