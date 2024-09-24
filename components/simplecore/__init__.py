# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import subprocess

import service
import toolbox
import toolbox.stats
import riscv.constants


class InternalService:
    def __init__(self):
        self.fifo = []
    def tx(self, msg): self.fifo.append(msg)
    def rx(self): pass
    def clear(self): self.fifo = []
    def __iter__(self): return iter(self.fifo)
    def __len__(self): return len(self.fifo)
    def pop(self, x): return self.fifo.pop(x)
class SimpleCore(dict):
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if not s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.futures = {}
        self.internal = {'service': InternalService()}
    def state(self):
        return {
            'service': self.get('name'),
            'cycle': self.get('cycle'),
            'coreid': self.get('coreid'),
        }
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def handle(self):
        _service = self.internal.get('service')
        _fifo = []
        logging.debug('@{:15}'.format(self.cycle))
        logging.debug('SimpleCore.handle(): futures : {}'.format(self.futures))
        logging.debug('_service.fifo : {}'.format(_service.fifo))
        while len(self.internal.get('service')):
            _msg = self.internal.get('service').pop(0)
            logging.debug('SimpleCore.handle(): _msg : {}'.format(_msg))
            _channel, _payload = next(iter(_msg.items()))
            logging.debug('SimpleCore.handle(): {} {}'.format(_channel, _payload))
            if _channel not in ['result', 'event']:
                _fifo.append(_msg)
                continue
            assert 'arrival' in _payload.keys(), '_msg : {} => _channel : {}, _payload : {}'.format(_msg, _channel, _payload)
            assert 'coreid' in _payload.keys(), '_msg : {} => _channel : {}, _payload : {}'.format(_msg, _channel, _payload)
            _arr = _payload.pop('arrival')
            _coreid = _payload.pop('coreid')
            logging.debug('SimpleCore.handle(): {} {} {}'.format(_arr, _coreid, _payload))
            logging.debug('SimpleCore.handle(): {} in self.internal.result_names : {}'.format(next(iter(_payload.keys())), next(iter(_payload.keys())) in self.internal.get('result_names')))
            logging.debug('SimpleCore.handle(): {} in self.internal.event_names  : {}'.format(next(iter(_payload.keys())), next(iter(_payload.keys())) in self.internal.get('event_names')))
            assert _arr > self.cycle, 'Attempting to schedule arrival in the past ({} vs. {})'.format(self.cycle, _arr)
            if 'result' == _channel and next(iter(_payload.keys())) in self.internal.get('result_names'):
                _res_evt = self.futures.get(_arr, {'results': [], 'events': []})
                _res_evt.get('results').append(_payload)
                self.futures.update({_arr: _res_evt})
            elif 'event' == _channel and next(iter(_payload.keys())) in self.internal.get('event_names'):
                _res_evt = self.futures.get(_arr, {'results': [], 'events': []})
                _res_evt.get('events').append(_payload)
                self.futures.update({_arr: _res_evt})
            else:
                _fifo.append({_channel: {**{'arrival': _arr, 'coreid': _coreid}, **_payload}})
            logging.debug('SimpleCore.handle(): futures : {}'.format(self.futures))
        _service.fifo = _fifo
        logging.debug('_service.fifo : {}'.format(_service.fifo))
    def do_results(self, results): pass
    def do_events(self, events): pass
    def do_tick(self, results, events): pass
