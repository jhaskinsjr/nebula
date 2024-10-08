# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import functools
import time

import service
import toolbox
import toolbox.stats
import simplecache

def fetch_block_0(service, state, coreid, addr, physical):
    _blockaddr = state.get('cache').blockaddr(addr)
    _blocksize = state.get('cache').nbytesperblock
#    state.get('pending_fetch').append(_blockaddr)
    state.get('pending_fetch').append({'blockaddr': _blockaddr, 'coreid': coreid})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': coreid,
        state.get('next'): {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
            **({'physical': True} if physical else {}),
        },
    }})
#    toolbox.report_stats(service, state, 'flat', '{}_misses'.format(state.get('service')))
    state.get('stats').refresh('flat', '{}_misses'.format(state.get('service')))
def do_cache_0(service, state, coreid, addr, size, physical, data=None):
    service.tx({'info': 'addr : {}'.format(addr)})
    _ante = None
    _post = None
    if state.get('cache').fits(addr, size):
        _data = state.get('cache').peek(addr, size)
        if not _data:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, coreid, addr, physical)
            return
    else:
        _blockaddr = state.get('cache').blockaddr(addr)
        _blocksize = state.get('cache').nbytesperblock
        _size = _blockaddr + _blocksize - addr
        _ante = state.get('cache').peek(addr, _size)
        if not _ante:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, coreid, addr, physical)
            return
        _post = state.get('cache').peek(addr + _size, size - _size)
        if not _post:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, coreid, addr + _size, physical)
            return
        # NOTE: In an L1DC with only a single block, an incoming _post would
        #       always displace _ante, and an incoming _ante would always displace
        #       _post... but an L1DC with only a single block would not be very
        #       useful in practice, so no effort will be made to handle that scenario.
        #       Like: No effort AT ALL.
        _data = _ante + _post
        assert len(_data) == size
    if data:
        # POKE
        service.tx({'result': {
            'arrival': state.get('config').get('hitlatency') + state.get('cycle'),
            'coreid': coreid,
            state.get('service'): {
                'addr': addr,
                'size': size,
            },
        }})
        if _ante:
            assert _post
            state.get('cache').poke(addr, _ante)
            state.get('cache').misc(addr, {'coreid': coreid})
            state.get('cache').poke(addr + size, _post)
            state.get('cache').misc(addr + size, {'coreid': coreid})
        else:
            state.get('cache').poke(addr, data)
            state.get('cache').misc(addr, {'coreid': coreid})
        # writethrough
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': coreid,
            state.get('next'): {
                'cmd': 'poke',
                'addr': addr,
                'size': len(data),
                'data': data,
                **({'physical': True} if physical else {}),
            }
        }})
    else:
        # PEEK
        service.tx({'result': {
            'arrival': state.get('config').get('hitlatency') + state.get('cycle'), # must not arrive in commit the same cycle as the LOAD instruction
            'coreid': coreid,
            state.get('service'): {
                'addr': addr,
                'size': size,
                'data': _data,
            },
        }})
    state.get('executing').pop(0)
    if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
#    toolbox.report_stats(service, state, 'flat', '{}_accesses'.format(state.get('service')))
    state.get('stats').refresh('flat', '{}_accesses'.format(state.get('service')))
def do_tick_0(service, state, results, events):
    for _coreid, rs in map(lambda y: (y.get('coreid'), y.get(state.get('next'))), filter(lambda x: x.get(state.get('next')), results)):
        service.tx({'info': 'rs : {} (_coreid : {})'.format(rs, _coreid)})
        service.tx({'info': 'state.pending_fetch : {}'.format(state.get('pending_fetch'))})
        service.tx({'info': 'state.executing     : {}'.format(state.get('executing'))})
        _addr = rs.get('addr')
        _data = rs.get('data')
        if not _data: continue
        if any(map(lambda x: _addr == x.get('blockaddr'), state.get('pending_fetch'))):
            service.tx({'info': 'rs : {}'.format(rs)})
            state.get('cache').poke(_addr, _data)
            state.get('cache').misc(_addr, {'coreid': _coreid})
            state.update({'pending_fetch': list(filter(lambda x: _addr != x.get('blockaddr'), state.get('pending_fetch')))})
    for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
        _cmd = _perf.get('cmd')
        if 'report_stats' == _cmd:
            _dict = state.get('stats').get(state.get('coreid', -1)).get(state.get('service'))
            toolbox.report_stats_from_dict(service, state, _dict)
    for _coreid, ev in map(lambda y: (y.get('coreid'), y.get(state.get('service'))), filter(lambda x: x.get(state.get('service')), events)):
        ev = {**ev, **{'coreid': _coreid}}
        service.tx({'info': 'ev : {} (_coreid : {})'.format(ev, _coreid)})
        service.tx({'info': 'state.pending_fetch : {}'.format(state.get('pending_fetch'))})
        if 'cmd' in ev.keys():
            if 'purge' == ev.get('cmd'):
                state.get('cache').purge()
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': _coreid,
                    state.get('next'): {
                        'cmd': 'purge',
                    },
                }})
                continue
            if 'invalidate' == ev.get('cmd'):
                state.get('cache').invalidate(**{'misc': {'coreid': _coreid}})
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': _coreid,
                    state.get('next'): {
                        'cmd': 'invalidate',
                    },
                }})
                continue
        state.get('executing').append(ev)
        service.tx({'info': 'state.executing : {}'.format(state.get('executing'))})
    if len(state.get('executing')):
        _op = state.get('executing')[0] # forcing single outstanding operation for now
        # NOTE: _op.get('cmd') assumed to be 'poke' if message contains a payload (i.e., _op.get('data') != None)
        _coreid = _op.get('coreid')
        _physical = _op.get('physical')
        _addr = _op.get('addr')
        _size = _op.get('size')
        _data = _op.get('data')
        do_cache(service, state, _coreid, _addr, _size, _physical, _data)




def fetch_block(service, state, op):
#    toolbox.report_stats(service, state, 'flat', '{}_misses'.format(state.get('service')))
    state.get('stats').refresh('flat', '{}_misses'.format(state.get('service')))
    _blockaddr = state.get('cache').blockaddr(op.get('addr'))
    _blocksize = state.get('cache').nbytesperblock
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': op.get('coreid'),
        state.get('next'): {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
            **({'physical': True} if op.get('physical') else {}),
        },
    }})
def do_cache(service, state, op):
    _data = state.get('cache').peek(op.get('addr'), op.get('size'))
    if not _data or state.get('cache').misc(op.get('addr')).get('coreid') != op.get('coreid'):
        if 'blockaddr' not in op.keys(): fetch_block(service, state, op)
        return ({**op, **{'blockaddr': state.get('cache').blockaddr(op.get('addr'))}} if 'blockaddr' not in op.keys() else op)
    if op.get('data'):
        # POKE
        state.get('cache').poke(op.get('addr'), op.get('data'))
        state.get('cache').misc(op.get('addr'), {'coreid': op.get('coreid')})
        # writethrough
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': op.get('coreid'),
            state.get('next'): {
                'cmd': 'poke',
                'addr': op.get('addr'),
                'size': len(op.get('data')),
                'data': op.get('data'),
                **({'physical': True} if op.get('physical') else {}),
            }
        }})
    else:
        # PEEK
        pass
#    toolbox.report_stats(service, state, 'flat', '{}_accesses'.format(state.get('service')))
    state.get('stats').refresh('flat', '{}_accesses'.format(state.get('service')))
    return {**op, **{'done': True, 'hit': 'blockaddr' not in op.keys()}}

def do_tick(service, state, results, events):
    def fusable(a, b): return 'ante' in a.keys() and 'post' in b.keys() and a.get('ante') == b.get('post') and a.get('done') and b.get('done')
    def fuse(a, b): return {
        **{k:v for k, v in a.items() if k not in ['ante', 'data', 'hit']},
        **({'data': a.get('data') + b.get('data')} if 'data' in a.keys() else {}),
        **{'hit': all(map(lambda x: x.get('hit'), [a, b]))},
    }
    for _coreid, rs in map(lambda y: (y.get('coreid'), y.get(state.get('next'))), filter(lambda x: x.get(state.get('next')), results)):
        service.tx({'info': 'rs : {} (_coreid : {})'.format(rs, _coreid)})
        service.tx({'info': 'state.executing     : {}'.format(state.get('executing'))})
        _addr = rs.get('addr')
        _data = rs.get('data')
        if not _data: continue
        if any(map(lambda x: _addr == x.get('blockaddr'), state.get('executing'))):
#        if any(map(lambda x: _addr == x.get('blockaddr') and _coreid == x.get('coreid'), state.get('executing'))):
            service.tx({'info': 'rs : {}'.format(rs)})
            state.get('cache').poke(_addr, _data)
            state.get('cache').misc(_addr, {'coreid': _coreid})
    for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
        _cmd = _perf.get('cmd')
        if 'report_stats' == _cmd:
            _dict = state.get('stats').get(state.get('coreid', -1)).get(state.get('service'))
            toolbox.report_stats_from_dict(service, state, _dict)
    for _coreid, ev in map(lambda y: (y.get('coreid'), y.get(state.get('service'))), filter(lambda x: x.get(state.get('service')), events)):
        ev = {**ev, **{'coreid': _coreid}}
        service.tx({'info': 'ev : {} (_coreid : {})'.format(ev, _coreid)})
        if 'cmd' in ev.keys():
            if 'purge' == ev.get('cmd'):
                state.get('cache').purge()
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': _coreid,
                    state.get('next'): {
                        'cmd': 'purge',
                    },
                }})
                continue
            if 'invalidate' == ev.get('cmd'):
                state.get('cache').invalidate(**{'misc': {'coreid': _coreid}})
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': _coreid,
                    state.get('next'): {
                        'cmd': 'invalidate',
                    },
                }})
                continue
        if state.get('cache').fits(ev.get('addr'), ev.get('size')):
            state.get('executing').append(ev)
        else:
            _ante = {k:v for k, v in ev.items()}
            _post = {k:v for k, v in ev.items()}
            _blockaddr = state.get('cache').blockaddr(ev.get('addr'))
            _blocksize = state.get('cache').nbytesperblock
            _ante.update({'ante': state.get('antepost')})
            _ante.update({'size': _blockaddr + _blocksize - ev.get('addr')})
            if 'data' in ev.keys(): _ante.update({'data': ev.get('data')[:_ante.get('size')]})
            _post.update({'post': state.get('antepost')})
            _post.update({'addr': ev.get('addr') + _ante.get('size')})
            _post.update({'size': ev.get('size') - _ante.get('size')})
            if 'data' in ev.keys(): _post.update({'data': ev.get('data')[_ante.get('size'):]})
            state.get('executing').append(_ante)
            state.get('executing').append(_post)
            state.update({'antepost': 1 + state.get('antepost')})
        service.tx({'info': 'state.executing : {}'.format(state.get('executing'))})
    state.update({'executing': list(map(lambda op: do_cache(service, state, op), state.get('executing')))})
    state.update({'executing': functools.reduce(
        lambda a, b: (a[:-1] + [fuse(a[-1], b)] if len(a) and fusable(a[-1], b) else a + [b]),
        state.get('executing'),
        [],
    )})
    for op in state.get('executing'):
        if not op.get('done') or any(map(lambda x: x in op.keys(), ['ante', 'post'])): continue
        service.tx({'result': {
            'arrival': (state.get('config').get('hitlatency') if 'hit' in op.keys() else 1) + state.get('cycle'),
            'coreid': op.get('coreid'),
            state.get('service'): {
                'addr': op.get('addr'),
                'size': op.get('size'),
                **({} if 'data' in op.keys() else {'data': state.get('cache').peek(op.get('addr'), op.get('size'))}) # NOTE: 'data' in op.keys() => POKE, which don't echo 'data' in 'result'
            },
        }})
    state.update({'executing': list(filter(lambda op: not op.get('done'), state.get('executing')))})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Shared Cache')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--name', type=str, dest='name', default=None, help='component name, e.g., "l3"')
    parser.add_argument('--next', type=str, dest='next', default=None, help='next level in memory hierarchy, e.g., "mem"')
    parser.add_argument('--cores', type=str, dest='cores', default=None, help='cores covered by this shared cache, e.g., "0:3"')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
    args = parser.parse_args()
    assert not os.path.isfile(args.log), '--log must point to directory, not file'
    while not os.path.isdir(args.log):
        try:
            os.makedirs(args.log, exist_ok=True)
        except:
            time.sleep(0.1)
    logging.basicConfig(
        filename=os.path.join(args.log, '{}_{}.log'.format(os.path.basename(__file__), args.cores)),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = {
        'service': (args.name if args.name else os.path.basename(os.path.splitext(sys.argv[0])[0])),
        'cycle': 0,
        'booted': False,
        'cache': None,
#        'pending_fetch': [],
        'active': True,
        'running': False,
        'ack': True,
        'executing': [],
        'antepost': 0,
        'stats': None,
        'next': args.next,
        'cores': (tuple(range(*(lambda a, b: (a, 1+b))(*map(lambda x: int(x), args.cores.split('-')))))),
        'config': {
            'nsets': 2**5,
            'nways': 2**4,
            'nbytesperblock': 2**6,
            'evictionpolicy': 'lru',
            'hitlatency': 25,
        },
    }
    _service = service.Service(state.get('service'), state.get('coreid', -1), _launcher.get('host'), _launcher.get('port'))
    while state.get('active'):
        state.update({'ack': True})
        msg = _service.rx()
#        _service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif 'reset' == k:
                _coreid = v.get('coreid')
                state.update({'executing': list(filter(lambda x: _coreid != x.get('coreid'), state.get('executing')))})
#                state.update({'pending_fetch': list(filter(lambda x: _coreid != x.get('coreid'), state.get('pending_fetch')))})
                if state.get('booted'):
                    state.get('cache').invalidate(**{'misc': {'coreid': _coreid}})
#                    state.get('cache').purge()
                logging.info('@{:15} : {}'.format(state.get('cycle'), msg))
            elif {'text': 'run'} == {k: v}:
                state.update({'running': True})
                state.update({'ack': False})
                if not state.get('booted'):
                    state.update({'booted': True})
#                    state.update({'pending_fetch': []})
                    state.update({'executing': []})
                    state.update({'stats': toolbox.stats.CounterBank(state.get('coreid', -1), state.get('service'))})
                    state.update({'cache': simplecache.SimpleCache(
                        state.get('config').get('nsets'),
                        state.get('config').get('nways'),
                        state.get('config').get('nbytesperblock'),
                        state.get('config').get('evictionpolicy'),
                    )})
                _service.tx({'info': 'state.config : {} (state.cores : {})'.format(state.get('config'), state.get('cores'))})
                logging.info('state : {}'.format(state))
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: x.get('coreid') in state.get('cores'), v.get('results')))
                _events = tuple(filter(lambda x:  x.get('coreid') in state.get('cores'), v.get('events')))
                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
