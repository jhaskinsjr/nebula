import os
import sys
import argparse
import logging

import service
import toolbox
import riscv.constants
import riscv.decode

def do_tick(service, state, results, events):
    for pc in map(lambda w: w.get('data'), filter(lambda x: x and '%pc' == x.get('name'), map(lambda y: y.get('register'), results))):
        service.tx({'info': 'pc            : {}'.format(pc)})
        service.tx({'info': 'state.get(pc) : {}'.format(state.get('%pc'))})
        if pc != state.get('%pc'):
            state.get('buffer').clear()
        state.update({'%pc': pc})
    for ev in filter(lambda x: x, map(lambda y: y.get('decode'), events)):
        _bytes = ev.get('bytes')
        state.get('buffer').extend(_bytes)
        service.tx({'info': 'buffer : {}'.format(list(map(lambda x: hex(x), state.get('buffer'))))})
        _decoded = riscv.decode.do_decode(state.get('buffer'), 1) # HACK: hard-coded max-instructions-to-decode of 1
        for _insn in _decoded: toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
#        service.tx({'info': '_decoded : {}'.format(_decoded)})
        _bytes_decoded = sum(map(lambda x: x.get('size'), _decoded))
        state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_bytes_decoded + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
        for _ in range(_bytes_decoded): state.get('buffer').pop(0)
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'insns': {
                'data': _decoded,
            },
        }})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Instruction Decode')
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
        'service': 'decode',
        'cycle': 0,
        'active': True,
        'running': False,
        '%pc': None,
        'ack': True,
        'buffer': [],
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
