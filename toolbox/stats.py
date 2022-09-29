import os
import sys
import argparse
import logging

import service

import json

def do_tick(service, state, results, events):
    for _stats in map(lambda y: y.get('stats'), filter(lambda x: x.get('stats'), events)):
        service.tx({'info': '_stats : {}'.format(_stats)})
        _s = _stats.get('service')
        _t = _stats.get('type')
        _n = _stats.get('name')
        _d = _stats.get('data')
        if not _s in state.get('stats').keys(): state.get('stats').update({_s: {}})
        if not _n in state.get('stats').get(_s): state.get('stats').get(_s).update({_n : ({} if 'histo' == _t else 0)})
        if 'histo' == _t:
            assert _d != None, 'Histogram-type stat {}:{} requires "data" field ({})'.format(_s, _n, _stats)
            state.get('stats').get(_s).get(_n).update({_d: 1 + state.get('stats').get(_s).get(_n).get(_d, 0)})
        else:
            state.get('stats').get(_s).update({_n: 1 + state.get('stats').get(_s).get(_n)})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Statistics')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
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
    state = {
        'service': 'stats',
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'stats': {
            'message_size': {},
            'cycle': 0,
        },
        'config': {
            'output_filename': None,
        },
    }
    _service = service.Service(state.get('service'), _launcher.get('host'), _launcher.get('port'))
    while state.get('active'):
        state.update({'ack': True})
        msg = _service.rx()
        _tmp = json.dumps(msg)
        state.get('stats').get('message_size').update({len(_tmp): 1 + state.get('stats').get('message_size').get(len(_tmp), 0)})
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    _output_filename = state.get('config').get('output_filename')
    fp = (sys.stdout if not _output_filename else open(_output_filename, 'w'))
    json.dump(state.get('stats'), fp)