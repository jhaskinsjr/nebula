# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import riscv.constants

def do_tick(service, state, results, events):
    for ev in filter(lambda x: x, map(lambda y: y.get('register'), events)):
        _cmd = ev.get('cmd')
        _name = ev.get('name')
        _data = ev.get('data')
        if 'set' == _cmd:
            assert _name in state.get('registers').keys()
            assert isinstance(_data, list)
            if 0 != _name:
                state.update({'registers': setregister(state.get('registers'), _name, _data)})
            toolbox.report_stats(service, state, 'histo', 'set.register', _name)
        elif 'get' == _cmd:
            assert _name in state.get('registers').keys()
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'register': {
                    'name': _name,
                    'data': getregister(state.get('registers'), _name),
                }
            }})
            toolbox.report_stats(service, state, 'histo', 'get.register', _name)
        else:
            logging.fatal('ev   : {}'.format(ev))
            logging.fatal('_cmd : {}'.format(_cmd))
            assert False

def setregister(registers, reg, val):
    return {x: y for x, y in tuple(registers.items()) + ((reg, val),)}
def getregister(registers, reg):
    return registers.get(reg, None)
def snapshot(service, state, addr, mainmem_filename):
    logging.debug('snapshot({}, {})'.format(addr, mainmem_filename))
    fd = os.open(mainmem_filename, os.O_RDWR)
    os.lseek(fd, addr, os.SEEK_SET)
    for k in ['%pc'] + sorted(filter(lambda x: not '%pc' == x, state.get('registers').keys()), key=str):
        v = getregister(state.get('registers'), k)
        os.write(fd, bytes(v))
        os.lseek(fd, 8, os.SEEK_CUR)
        service.tx({'info': 'snapshot: {} : {}'.format(k, v)})
    os.fsync(fd)
    os.close(fd)
    toolbox.report_stats(service, state, 'flat', 'snapshot')

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
    state = {
        'service': 'regfile',
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'registers': {
            **{'%pc': riscv.constants.integer_to_list_of_bytes(0, 64, 'little')},
            **{x: riscv.constants.integer_to_list_of_bytes(0, 64, 'little') for x in range(32)},
            **{0x1000_0000 + x: riscv.constants.integer_to_list_of_bytes(0, 64, 'little') for x in range(32)}, # FP registers
        }
    }
    _service = service.Service(state.get('service'), _launcher.get('host'), _launcher.get('port'))
    while state.get('active'):
        state.update({'ack': True})
        msg = _service.rx()
#        _service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif {'text': 'run'} == {k: v}:
                state.update({'running': True})
                state.update({'ack': False})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                if v.get('snapshot'):
                    _addr = v.get('snapshot').get('addr')
                    _mainmem_filename = v.get('snapshot').get('mainmem_filename')
                    snapshot(_service, state, _addr.get('register'), _mainmem_filename)
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _snapshot_filename = v.get('snapshot_filename')
                _addr = v.get('addr')
                fd = os.open(_snapshot_filename, os.O_RDWR)
                os.lseek(fd, _addr.get('register'), os.SEEK_SET)
                for k in ['%pc'] + sorted(filter(lambda x: not '%pc' == x, state.get('registers').keys()), key=str):
                    v = list(os.read(fd, 8))
                    os.lseek(fd, 8, os.SEEK_CUR)
                    state.update({'registers': setregister(state.get('registers'), k, v)})
                    _service.tx({'info': 'restore: {} : {}'.format(k, v)})
                os.close(fd)
                toolbox.report_stats(_service, state, 'flat', 'restore')
                _service.tx({'register': {
                    'cmd': 'set',
                    'name': '%pc',
                    'data': getregister(state.get('registers'), '%pc'),
                }})
            elif 'register' == k:
                _cmd = v.get('cmd')
                _name = v.get('name')
                if 'set' == _cmd:
                    state.update({'registers': setregister(state.get('registers'), _name, v.get('data'))})
                elif 'get' == _cmd:
                    _ret = getregister(state.get('registers'), _name)
                    _service.tx({'result': {'register': _ret}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    for k, v in state.get('registers').items():
        logging.info('register {:2} : {}'.format(k, v))