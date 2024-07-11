# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import itertools
import logging

import service

import json

def log2(A):
    return (
        None
        if 1 > A else
        len(list(itertools.takewhile(lambda x: x, map(lambda y: A >> y, range(A))))) - 1
    )

class CounterBank(dict):
    def __init__(self): pass
    def refresh(self, coreid, svc, typ, name, data=None, **kwargs):
        if not coreid in self.keys(): self.update({coreid: {}})
        if not svc in self.get(coreid).keys(): self.get(coreid).update({svc: {}})
        if not name in self.get(coreid).get(svc): self.get(coreid).get(svc).update({name : ({} if 'histo' == typ else 0)})
        _increment = (kwargs.get('increment') if kwargs and kwargs.get('increment') else 1)
        if 'histo' == typ:
            assert data != None, 'Histogram-type stat {}_{}:{} requires "data" field'.format(coreid, svc, name)
            self.get(coreid).get(svc).get(name).update({data: _increment + self.get(coreid).get(svc).get(name).get(data, 0)})
        elif 'dict' == typ:
            assert isinstance(data, dict)
            assert data != None, 'Histogram-type stat {}_{}:{} requires "data" field'.format(coreid, svc, name)
            self.get(coreid).get(svc).update({name: data})
        else:
            self.get(coreid).get(svc).update({name: _increment + self.get(coreid).get(svc).get(name)})
class SimpleStat:
    def __init__(self, name, launcher, s=None, **kwargs):
        self.name = name
        self.service = (service.Service(self.get('name'), self.get('coreid', -1), launcher.get('host'), launcher.get('port')) if not s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = CounterBank()
        self.stats.update({'message_size': {}})
        self.stats.update({'cycle': 0})
        self.config = {
            'output_filename': kwargs.get('output_filename', None),
        }
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def do_tick(self, results, events):
        for _coreid, _stats in map(lambda y: (y.get('coreid', -1), y.get('stats')), filter(lambda x: x.get('stats'), events)):
            logging.debug('do_tick(): [{:04}] _stats : {}'.format(_coreid, _stats))
            _s = _stats.get('service')
            _t = _stats.get('type')
            _n = _stats.get('name')
            _d = _stats.get('data')
            _k = _stats.get('kwargs')
            try:
                self.stats.refresh(_coreid, _s, _t, _n, _d, **{**(_k if _k else {})})
            except:
                logging.error('Failed stat refresh! ({:04}: {})'.format(_coreid, _stats))



if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Statistics')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--output_filename', type=str, dest='output_filename', default=None, help='file to output JSON results to')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
    args = parser.parse_args()
    logging.basicConfig(
        filename=os.path.join(args.log, '{}.log'.format(os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = SimpleStat('stats', _launcher, **{
        'output_filename': args.output_filename,
    })
    while state.get('active'):
        state.update({'ack': True})
        msg = state.service.rx()
        _tmp = json.dumps(msg)
        state.get('stats').get('message_size').update({2**log2(len(_tmp)): 1 + state.get('stats').get('message_size').get(2**log2(len(_tmp)), 0)})
        state.get('stats').update({'cycle': state.get('cycle')})
#        _service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif {'text': 'run'} == {k: v}:
                state.update({'running': True})
                state.update({'ack': False})
                state.service.tx({'info': 'state.config : {}'.format(state.get('config'))})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'config' == k:
                logging.info('config : {}'.format(v))
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
        if state.get('ack') and state.get('running'): state.service.tx({'ack': {'cycle': state.get('cycle'), 'msg': msg}})
    fp = (sys.stdout if not state.get('config').get('output_filename') else open(state.get('config').get('output_filename'), 'w'))
    json.dump(state.get('stats'), fp, indent=4)
    logging.info('state.stats : {}'.format(state.get('stats')))