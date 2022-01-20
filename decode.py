import sys
import argparse

import service

import struct
import functools

def illegal_instruction(word):
    assert False, 'Illegal instruction ({:08x})!'.format(word)
def unimplemented_instruction(word):
    return {
        'cmd': 'Undefined',
        'word': word,
    }
def auipc(word):
    return {
        'cmd': 'AUIPC',
        'imm': uncompressed_imm32(word, signed=True),
        'word': word,
    }
def jal(word):
    return {
        'cmd': 'JAL',
        'imm': uncompressed_imm21(word, signed=True),
        'rd': uncompressed_rd(word),
        'word': word,
    }

def decode_compressed(word):
    return {
    }.get(compressed_opcode(word), unimplemented_instruction)(word)
def decode_uncompressed(word):
    return {
        0b001_0111: auipc,
        0b110_1111: jal,
    }.get(uncompressed_opcode(word), unimplemented_instruction)(word)

def uncompressed_opcode(word):
    return (word & 0b111_1111)

def compressed_opcode(word):
    return ((word & 0b1110_0000_0000_0000) >> 11) | (word & 0b11)
def compressed_rs1(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 7) & 0b1_1111
def compressed_rs1_prime(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 7) & 0b111
compressed_rd = compressed_rs1
compressed_rd_prime = compressed_rs1_prime

def uncompressed_rd(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 7) & 0b1_1111

def compressed_imm6(word, **kwargs):
    # nzimm[5] 00000 nzimm[4:0]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    _b05         = (word & 0b1_0000_0000_0000) >> 12
    _b0403020100 = (word & 0b111_1100) >> 2
    _retval  = _b05 << 5
    _retval |= _b0403020100
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b05 << x, range(6, 8)), _retval)
    return int.from_bytes(struct.Struct('<B').pack(_retval), 'little', **kwargs)
def compressed_imm10(word, **kwargs):
    # nzimm[9] 00010 nzimm[4|6|8:7|5]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    _tmp = (word >> 2) & 0b111_1111_1111
    _b05   = (_tmp & 0b1) >> 0
    _b0807 = (_tmp & 0b110) >> 1
    _b06   = (_tmp & 0b1000) >> 3
    _b04   = (_tmp & 0b1_0000) >> 4
    _b09   = (_tmp & 0b100_0000_0000) >> 10
    _retval  = _b09 << 9
    _retval |= _b0807 << 7
    _retval |= _b06 << 6
    _retval |= _b05 << 5
    _retval |= _b04 << 4
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b09 << x, range(10, 16)), _retval)
    return int.from_bytes(struct.Struct('<H').pack(_retval), 'little', **kwargs)
def compressed_imm12(word, **kwargs):
    # imm[11|4|9:8|10|6|7|3:1|5]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf, (p. 111)
    _tmp = (word & 0b0001_1111_1111_1100) >> 2
    _b05     = (_tmp & 0b1) >> 0
    _b030201 = (_tmp & 0b1110) >> 1
    _b07     = (_tmp & 0b1_0000) >> 4
    _b06     = (_tmp & 0b10_0000) >> 5
    _b10     = (_tmp & 0b100_0000) >> 6
    _b0908   = (_tmp & 0b1_1000_0000) >> 7
    _b04     = (_tmp & 0b10_0000_0000) >> 9
    _b11     = (_tmp & 0b100_0000_0000) >> 10
    _retval  = _b11 << 11
    _retval |= _b10 << 10
    _retval |= _b0908 << 8
    _retval |= _b07 << 7
    _retval |= _b06 << 6
    _retval |= _b05 << 5
    _retval |= _b04 << 4
    _retval |= _b030201 << 3
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 16)), _retval)
    return int.from_bytes(struct.Struct('<H').pack(_retval), 'little', **kwargs)
def uncompressed_imm21(word, **kwargs):
    # imm[20|10:1|11|19:12] rrrrr ooooooo
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _tmp = (word >> 12) & 0b1111_1111_1111_1111_1111
    _b1918171615141312     = (_tmp & 0b1111_1111) >> 0
    _b11                   = (_tmp & 0b1_0000_0000) >> 8
    _b10090807060504030201 = (_tmp & 0b111_1111_1110_0000_0000) >> 9
    _b20                   = (_tmp & 0b1000_0000_0000_0000_0000) >> 19
    _retval  = _b20 << 20
    _retval |= _b1918171615141312 << 12
    _retval |= _b11 << 11
    _retval |= _b10090807060504030201 << 1
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b20 << x, range(21, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_imm32(word, **kwargs):
    # imm[31:12] rrrrr ooooooo
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _retval = word & 0b1111_1111_1111_1111_1111_0000_0000_0000
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)


def do_decode(state, max_insns):
    _retval = []
    while max_insns > len(_retval) and len(state.get('buffer')):
        _word = int.from_bytes(state.get('buffer')[:4], 'little')
        if 0x3 == _word & 0x3:
            if 4 > len(state.get('buffer')): break
            _retval.append(decode_uncompressed(_word))
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
        else:
            _word &= 0xffff
            _retval.append(decode_compressed(_word))
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
    return _retval

def do_tick(service, state, results, events):
    for ev in filter(lambda x: x, map(lambda y: y.get('decode'), events)):
        _bytes = ev.get('bytes')
        state.get('buffer').extend(_bytes)
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'insns': {
                'data': do_decode(state, 1), # HACK: hard-coded max-instructions-to-decode of 1
            },
        }})

def setregister(registers, reg, val):
    return {x: y for x, y in tuple(registers.items()) + ((reg, val),)}
def getregister(registers, reg):
    return registers.get(reg, None)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Instruction Decode')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    _service = service.Service('decode', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'buffer': [],
    }
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