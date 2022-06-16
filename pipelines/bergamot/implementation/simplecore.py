import os
import sys
import argparse
import logging

import service
import toolbox
import riscv.constants


def do_tick(service, state, results, events):
    for pc in map(lambda w: w.get('data'), filter(lambda x: x and '%pc' == x.get('name'), map(lambda y: y.get('register'), results))):
        if 0 == int.from_bytes(pc, 'little'):
            service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
            service.tx({'shutdown': None})
        if not state.get('%jp'): state.update({'%jp': pc})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'mem': {
                'cmd': 'peek',
                'addr': int.from_bytes(state.get('%jp'), 'little'),
                'size': 4,
            },
        }})
        state.update({'pending_fetch': int.from_bytes(state.get('%jp'), 'little')})
        state.update({'%jp': riscv.constants.integer_to_list_of_bytes(4 + int.from_bytes(state.get('%jp'), 'little'), 64, 'little')})
        state.update({'%pc': pc})
        state.update({'pending_pc': False})
        toolbox.report_stats(service, state, 'flat', 'fetches')
    for mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
#        service.tx({'info': 'mem.addr      : {}'.format(mem.get('addr'))})
#        service.tx({'info': 'pending_fetch : {}'.format(state.get('pending_fetch'))})
        if mem.get('addr') != state.get('pending_fetch'):
            continue
        state.update({'pending_fetch': None})
        state.update({'pending_decode': True})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'decode': {
                'bytes': mem.get('data'),
            },
        }})
    for insns in filter(lambda x: x, map(lambda y: y.get('insns'), results)):
        state.update({'pending_decode': False})
        state.update({'pending_execute': insns.get('data')})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'execute': {
                'insns': insns.get('data'), 
            }
        }})
    for completed in filter(lambda x: x, map(lambda y: y.get('complete'), events)):
        _completed = {'insns': [{x: y for x, y in filter(lambda z: 'taken' not in z, a.items())} for a in completed.get('insns')]}
        _pending = {'insns': [{x: y for x, y in filter(lambda z: 'taken' not in z, a.items())} for a in state.get('pending_execute')]}
#        service.tx({'info': 'completed  : {}'.format(completed)})
#        service.tx({'info': '_completed : {}'.format(_completed)})
#        service.tx({'info': 'state.get(pending_execute) : {}'.format(state.get('pending_execute'))})
#        service.tx({'info': '_pending   : {}'.format(_pending)})
        assert _completed.get('insns') == _pending.get('insns'), '{} != {}'.format(completed.get('insns'), state.get('pending_execute'))
        _insns = completed.get('insns')
        _jumps = any(map(lambda a: a.get('cmd') in riscv.constants.JUMPS, _insns))
        _taken_branches = any(map(lambda a: a.get('cmd') in riscv.constants.BRANCHES and a.get('taken'), _insns))
#        service.tx({'info': '%jp : {}'.format(state.get('%jp'))})
#        service.tx({'info': '%pc : {}'.format(state.get('%pc'))})
        if not _jumps and not _taken_branches:
            _pc = sum(map(lambda x: x.get('size'), completed.get('insns'))) + int.from_bytes(state.get('%pc'), 'little')
            _pc = riscv.constants.integer_to_list_of_bytes(_pc, 64, 'little')
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'register': {
                    'cmd': 'set',
                    'name': '%pc',
                    'data': _pc,
                }
            }})
            state.update({'%pc': _pc})
        else:
            state.update({'%jp': None})
#        service.tx({'info': '%jp : {}'.format(state.get('%jp'))})
#        service.tx({'info': '%pc : {}'.format(state.get('%pc'))})
        state.update({'pending_execute': None})
    _n_committed = len(list(filter(lambda x: x, map(lambda y: y.get('commit'), events))))
    if _n_committed: service.tx({'committed': _n_committed})
    for committed in filter(lambda x: x, map(lambda y: y.get('commit'), events)):
        service.tx({'info': 'retiring : {}'.format(committed)})
#        _n_committed += 1
    if not state.get('pending_pc') and not state.get('pending_fetch') and not state.get('pending_decode') and not state.get('pending_execute'):
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': '%pc',
            },
        }})
        state.update({'pending_pc': True})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    logging.basicConfig(
        filename=os.path.join(args.log, '{}.log'.format(os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = {
        'service': 'simplecore',
        'cycle': 0,
        'active': True,
        'running': False,
        'pending_pc': False,
        'pending_fetch': None,
        'pending_decode': False,
        'pending_execute': None,
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        '%pc': None,
        'ack': True,
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
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))