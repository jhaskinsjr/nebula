# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import riscv.constants

class SimpleRegisterFile:
    def __init__(self, name, launcher, s=None):
        self.name = name
        self.service = (service.Service(self.get('name'), launcher.get('host'), launcher.get('port')) if not s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.registers = {
            **{'%pc': riscv.constants.integer_to_list_of_bytes(0, 64, 'little')},
            **{x: riscv.constants.integer_to_list_of_bytes(0, 64, 'little') for x in range(32)},
            **{0x1000_0000 + x: riscv.constants.integer_to_list_of_bytes(0, 64, 'little') for x in range(32)}, # FP registers
        }
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
        for ev in filter(lambda x: x, map(lambda y: y.get('register'), events)):
            _cmd = ev.get('cmd')
            _name = ev.get('name')
            _data = ev.get('data')
            if 'set' == _cmd:
                assert _name in self.get('registers').keys()
                assert isinstance(_data, list)
#                if 0 != _name:
#                    self.update({'registers': self.setregister(self.get('registers'), _name, _data)})
                self.update({'registers': self.setregister(self.get('registers'), _name, _data)})
                toolbox.report_stats(self.service, self.state(), 'histo', 'set.register', _name)
            elif 'get' == _cmd:
                assert _name in self.get('registers').keys()
                self.service.tx({'result': {
                    'arrival': 1 + self.get('cycle'),
                    'register': {
                        'name': _name,
                        'data': self.getregister(self.get('registers'), _name),
                    }
                }})
                toolbox.report_stats(self.service, self.state(), 'histo', 'get.register', _name)
            else:
                logging.fatal('ev   : {}'.format(ev))
                logging.fatal('_cmd : {}'.format(_cmd))
                assert False
    def setregister(self, registers, reg, val):
#        return {x: y for x, y in tuple(registers.items()) + ((reg, val),)}
        return {x: y for x, y in tuple(registers.items()) + ((reg, val), (0, riscv.constants.integer_to_list_of_bytes(0, 64, 'little')))}
    def getregister(self, registers, reg):
        return registers.get(reg, None)
    def snapshot(self, addr, mainmem_filename):
        logging.debug('snapshot({}, {})'.format(addr, mainmem_filename))
        fd = os.open(mainmem_filename, os.O_RDWR)
        os.lseek(fd, addr, os.SEEK_SET)
        for k in ['%pc'] + sorted(filter(lambda x: not '%pc' == x, self.get('registers').keys()), key=str):
            v = self.getregister(self.get('registers'), k)
            os.write(fd, bytes(v))
            os.lseek(fd, 8, os.SEEK_CUR)
            self.service.tx({'info': 'snapshot: {} : {}'.format(k, v)})
        os.fsync(fd)
        os.close(fd)
        toolbox.report_stats(self.service, self.state(), 'flat', 'snapshot')

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Register File')
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
    state = SimpleRegisterFile('regfile', _launcher)
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
                state.update({'running': True})
                state.update({'ack': False})
                logging.info('state.registers : {}'.format(state.get('registers')))
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                if v.get('snapshot'):
                    _addr = v.get('snapshot').get('addr')
                    _mainmem_filename = v.get('snapshot').get('mainmem_filename')
                    state.snapshot(_addr.get('register'), _mainmem_filename)
                _results = v.get('results')
                _events = v.get('events')
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                state.service.tx({'ack': {'cycle': state.get('cycle')}})
                _snapshot_filename = v.get('snapshot_filename')
                _addr = v.get('addr')
                fd = os.open(_snapshot_filename, os.O_RDWR)
                os.lseek(fd, _addr.get('register'), os.SEEK_SET)
                for k in ['%pc'] + sorted(filter(lambda x: not '%pc' == x, state.get('registers').keys()), key=str):
                    v = list(os.read(fd, 8))
                    os.lseek(fd, 8, os.SEEK_CUR)
                    state.update({'registers': state.setregister(state.get('registers'), k, v)})
                    state.service.tx({'info': 'restore: {} : {}'.format(k, v)})
                os.close(fd)
                toolbox.report_stats(state.service, state.state(), 'flat', 'restore')
                state.service.tx({'register': {
                    'cmd': 'set',
                    'name': '%pc',
                    'data': state.getregister(state.get('registers'), '%pc'),
                }})
            elif 'register' == k:
                logging.info('register : {}'.format(v))
                _cmd = v.get('cmd')
                _name = v.get('name')
                if 'set' == _cmd:
                    state.update({'registers': state.setregister(state.get('registers'), _name, v.get('data'))})
                elif 'get' == _cmd:
                    _ret = state.getregister(state.get('registers'), _name)
                    state.service.tx({'result': {'register': _ret}})
        if state.get('ack') and state.get('running'): state.service.tx({'ack': {'cycle': state.get('cycle')}})
    for k, v in state.get('registers').items():
        logging.info('register {:2} : {}'.format(k, v))