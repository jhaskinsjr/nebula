import sys
import argparse
import functools
import struct

import service
import components.simplecache
import riscv.execute
import riscv.syscall.linux

def report_stats(service, state, type, name, data=None):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'stats': {
            **{
                'service': state.get('service'),
                'type': type,
                'name': name,
            },
            **({'data': data} if None != data else {}),
        },
    }})

def fetch_block(service, state, addr):
    _blockaddr = state.get('l1dc').blockaddr(addr)
    _blocksize = state.get('l1dc').nbytesperblock
    state.get('pending_fetch').append(_blockaddr)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'mem': {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
        },
    }})
    report_stats(service, state, 'flat', 'l1dc.misses')
def do_l1dc(service, state, addr, size, data=None):
    service.tx({'info': 'addr : {}'.format(addr)})
    if state.get('l1dc').fits(addr, size):
        _data = state.get('l1dc').peek(addr, size)
#        service.tx({'info': '_data : {}'.format(_data)})
        if not _data:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr)
            return
    else:
        _blockaddr = state.get('l1dc').blockaddr(addr)
        _blocksize = state.get('l1dc').nbytesperblock
        _size = _blockaddr + _blocksize - addr
        _ante = state.get('l1dc').peek(addr, _size)
        if not _ante:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr)
            return
        _post = state.get('l1dc').peek(addr + _size, size - _size)
        if not _post:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr + _size)
            return
        # NOTE: In an L1DC with only a single block, an incoming _post would
        #       always displace _ante, and an incoming _ante would always displace
        #       _post... but an L1DC with only a single block would not be very
        #       useful in practice, so no effort will be made to handle that scenario.
        #       Like: No effort AT ALL.
        _data = _ante + _post
        assert len(_data) == size
    if data:
        # STORE
        service.tx({'result': {
            'arrival': 2 + state.get('cycle'),
            'mem': {
                'addr': addr,
                'size': size,
            },
        }})
        # writethrough
        state.get('l1dc').poke(addr, data)
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'mem': {
                'cmd': 'poke',
                'addr': addr,
                'size': len(data),
                'data': data
            }
        }})
    else:
        # LOAD
        service.tx({'result': {
            'arrival': 2 + state.get('cycle'), # must not arrive in commit the same cycle as the LOAD instruction
            'mem': {
                'addr': addr,
                'size': size,
                'data': _data,
            },
        }})
    state.get('executing').pop(0)
    if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
    report_stats(service, state, 'flat', 'l1dc.accesses')

def do_unimplemented(service, state, insn):
#    print('Unimplemented: {}'.format(state.get('insn')))
    service.tx({'undefined': insn})

def do_load(service, state, insn):
    do_l1dc(service, state, insn.get('operands').get('addr'), insn.get('nbytes'))
def do_store(service, state, insn):
    _data = insn.get('operands').get('data')
    _data = {
        'SD': _data,
        'SW': _data[:4],
        'SH': _data[:2],
        'SB': _data[:1],
    }.get(insn.get('cmd'))
    do_l1dc(service, state, insn.get('operands').get('addr'), insn.get('nbytes'), _data)

def do_execute(service, state):
    # NOTE: simpliying to only one in-flight LOAD/STORE at a time
    _insn = (state.get('executing')[0] if len(state.get('executing')) else (state.get('pending_execute')[0] if len(state.get('pending_execute')) else None))
    if not _insn: return
    if not len(state.get('executing')): state.get('executing').append(state.get('pending_execute').pop(0))
    service.tx({'info': '_insn : {}'.format(_insn)})
#    if 0x3 == _insn.get('word') & 0x3:
#        print('do_execute(): @{:8} {:08x} : {}'.format(state.get('cycle'), _insn.get('word'), _insn.get('cmd')))
#    else:
#        print('do_execute(): @{:8}     {:04x} : {}'.format(state.get('cycle'), _insn.get('word'), _insn.get('cmd')))
    {
        'LD': do_load,
        'LW': do_load,
        'LH': do_load,
        'LB': do_load,
        'LWU': do_load,
        'LHU': do_load,
        'LBU': do_load,
        'SD': do_store,
        'SW': do_store,
        'SH': do_store,
        'SB': do_store,
    }.get(_insn.get('cmd'), do_unimplemented)(service, state, _insn)

def do_tick(service, state, results, events):
    for _mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
        _addr = _mem.get('addr')
        if _addr == state.get('operands').get('mem'):
            state.get('operands').update({'mem': _mem.get('data')})
        elif _addr in state.get('pending_fetch'):
            service.tx({'info': '_mem : {}'.format(_mem)})
            state.get('l1dc').poke(_addr, _mem.get('data'))
    for _insn in map(lambda y: y.get('lsu'), filter(lambda x: x.get('lsu'), events)):
        state.get('pending_execute').append(_insn.get('insn'))
        # TODO: should this commit event be done in alu like everything else?
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'commit': {
                'insn': _insn.get('insn'),
            }
        }})
    do_execute(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Load-Store Unit')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    state = {
        'service': 'lsu',
        'cycle': 0,
        'l1dc': None,
        'pending_fetch': [],
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
        'executing': [],
        'operands': {},
        'config': {
            'l1dc.nsets': 2**4,
            'l1dc.nways': 2**1,
            'l1dc.nbytesperblock': 2**4,
        },
    }
    state.update({'l1dc': components.simplecache.SimpleCache(
        state.get('config').get('l1dc.nsets'),
        state.get('config').get('l1dc.nways'),
        state.get('config').get('l1dc.nbytesperblock'),
    )})
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