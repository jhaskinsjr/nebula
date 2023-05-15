# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import subprocess

import regfile
import mainmem
import service
import toolbox
import riscv.decode
import riscv.execute
import riscv.constants
import riscv.syscall.linux

def getregister(regfile, reg):
    return regfile.getregister(regfile.registers, reg)
def setregister(regfile, reg, val):
    regfile.registers = regfile.setregister(regfile.registers, reg, val)

def do_unimplemented(insn, service, state, **kwargs):
    _regfile = kwargs.get('regfile')
    logging.info('Unimplemented: {}'.format(state.get('pending_execute')))
    service.tx({'undefined': insn})
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return insn
def do_lui(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    setregister(kwargs.get('regfile'), insn.get('rd'), riscv.execute.lui(insn.get('imm')))
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return insn
def do_auipc(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    setregister(kwargs.get('regfile'), insn.get('rd'), riscv.execute.auipc(insn.get('%pc'), insn.get('imm')))
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return insn
def do_jal(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _next_pc, _ret_pc = riscv.execute.jal(insn.get('%pc'), insn.get('imm'), insn.get('size'))
    setregister(_regfile, '%pc', _next_pc)
    setregister(_regfile, insn.get('rd'), _ret_pc)
    return {
        **insn,
        **{'next_pc': _next_pc},
        **{'ret_pc': _ret_pc},
    }
def do_jalr(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
    }
    _next_pc, _ret_pc = riscv.execute.jalr(insn.get('%pc'), insn.get('imm'), _operands.get('rs1'), insn.get('size'))
    setregister(_regfile, '%pc', _next_pc)
    setregister(_regfile, insn.get('rd'), _ret_pc)
    return {
        **insn,
        **{'operands': _operands},
        **{'next_pc': _next_pc},
        **{'ret_pc': _ret_pc},
    }
def do_branch(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
        'rs2': getregister(_regfile, insn.get('rs2')),
    }
    _next_pc, _taken = {
        'BEQ': riscv.execute.beq,
        'BNE': riscv.execute.bne,
        'BLT': riscv.execute.blt,
        'BGE': riscv.execute.bge,
        'BLTU': riscv.execute.bltu,
        'BGEU': riscv.execute.bgeu,
    }.get(insn.get('cmd'))(insn.get('%pc'), _operands.get('rs1'), _operands.get('rs2'), insn.get('imm'), insn.get('size'))
    setregister(_regfile, '%pc', _next_pc)
    return {
        **insn,
        **{'operands': _operands},
        **{'next_pc': _next_pc},
        **{'taken': _taken},
    }
def do_itype(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
    }
    _result = {
        'ADDI': riscv.execute.addi,
        'SLTI': riscv.execute.slti,
        'SLTIU': riscv.execute.sltiu,
        'ADDIW': riscv.execute.addiw,
        'XORI': riscv.execute.xori,
        'ORI': riscv.execute.ori,
        'ANDI': riscv.execute.andi,
    }.get(insn.get('cmd'))(_operands.get('rs1'), insn.get('imm'))
    setregister(_regfile, insn.get('rd'), _result)
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
        **{'result': _result},
    }
def do_rtype(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
        'rs2': getregister(_regfile, insn.get('rs2')),
    }
    _result = {
        'ADD': riscv.execute.add,
        'SUB': riscv.execute.sub,
        'XOR': riscv.execute.xor,
        'SLT': riscv.execute.slt,
        'SLTU': riscv.execute.sltu,
        'SLL': riscv.execute.sll,
        'SRL': riscv.execute.srl,
        'SRA': riscv.execute.sra,
        'OR': riscv.execute.do_or,
        'AND': riscv.execute.do_and,
        'ADDW': riscv.execute.addw,
        'SUBW': riscv.execute.subw,
        'SLLW': riscv.execute.sllw,
        'SRLW': riscv.execute.srlw,
        'SRAW': riscv.execute.sraw,
        'MUL': riscv.execute.mul,
        'MULH': riscv.execute.mulh,
        'MULHSU': riscv.execute.mulhsu,
        'MULHU': riscv.execute.mulhu,
        'DIV': riscv.execute.div,
        'DIVU': riscv.execute.divu,
        'REM': riscv.execute.rem,
        'REMU': riscv.execute.remu,
        'MULW': riscv.execute.mulw,
        'DIVW': riscv.execute.divw,
        'DIVUW': riscv.execute.divuw,
        'REMW': riscv.execute.remw,
        'REMUW': riscv.execute.remuw,
    }.get(insn.get('cmd'))(_operands.get('rs1'), _operands.get('rs2'))
    setregister(_regfile, insn.get('rd'), _result)
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
        **{'result': _result},
    }
def do_load(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _mainmem = kwargs.get('mainmem')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
    }
    _addr = insn.get('imm') + int.from_bytes(_operands.get('rs1'), 'little')
    _fetched  = _mainmem.peek(_addr, insn.get('nbytes'))
    _fetched += [-1] * (8 - len(_fetched))
    _data = { # HACK: This is 100% little-endian-specific
        'LD': _fetched,
        'LW': _fetched[:4] + [(0xff if ((_fetched[3] >> 7) & 0b1) else 0)] * 4,
        'LH': _fetched[:2] + [(0xff if ((_fetched[1] >> 7) & 0b1) else 0)] * 6,
        'LB': _fetched[:1] + [(0xff if ((_fetched[0] >> 7) & 0b1) else 0)] * 7,
        'LWU': _fetched[:4] + [0] * 4,
        'LHU': _fetched[:2] + [0] * 6,
        'LBU': _fetched[:1] + [0] * 7,
    }.get(insn.get('cmd'))
    setregister(_regfile, insn.get('rd'), _data)
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
        **{'data': _data},
    }
def do_store(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _mainmem = kwargs.get('mainmem')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
        'rs2': getregister(_regfile, insn.get('rs2')),
    }
    _data = _operands.get('rs2')
    _data = {
        'SD': _data,
        'SW': _data[:4],
        'SH': _data[:2],
        'SB': _data[:1],
    }.get(insn.get('cmd'))
    _addr = insn.get('imm') + int.from_bytes(_operands.get('rs1'), 'little')
    _mainmem.poke(_addr, insn.get('nbytes'), _data)
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
    }
def do_nop(insn, *args, **kwargs):
    return insn
def do_shift(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
    }
    _result = {
        'SLLI': riscv.execute.slli,
        'SRLI': riscv.execute.srli,
        'SRAI': riscv.execute.srai,
        'SLLIW': riscv.execute.slliw,
        'SRLIW': riscv.execute.srliw,
        'SRAIW': riscv.execute.sraiw,
    }.get(insn.get('cmd'))(_operands.get('rs1'), insn.get('shamt'))
    setregister(_regfile, insn.get('rd'), _result)
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
        **{'result': _result},
    }
def do_ecall(insn, *args, **kwargs):
    # FIXME: actually DO the ECALL
    _regfile = kwargs.get('regfile')
    _mainmem = kwargs.get('mainmem')
    _system = kwargs.get('system')
    _operands = {
        'syscall_num': getregister(_regfile, 17),
        'a0': getregister(_regfile, 10),
        'a1': getregister(_regfile, 11),
        'a2': getregister(_regfile, 12),
        'a3': getregister(_regfile, 13),
        'a4': getregister(_regfile, 14),
        'a5': getregister(_regfile, 15),
    }
    _side_effect = {}
    _syscall_kwargs = {}
    while not _side_effect.get('done'):
        _side_effect = _system.do_syscall(
            _operands.get('syscall_num'),
            _operands.get('a0'), _operands.get('a1'), _operands.get('a2'), _operands.get('a3'), _operands.get('a4'), _operands.get('a5'), **{
                **_syscall_kwargs,
                **{'cycle': insn.get('iid')},
            }
        )
        if 'poke' in _side_effect.keys():
            _addr = int.from_bytes(_side_effect.get('poke').get('addr'), 'little')
            _data = _side_effect.get('poke').get('data')
            _mainmem.poke(_addr, len(_data), _data)
        if 'peek' in _side_effect.keys():
            _addr = _side_effect.get('peek').get('addr')
            _size = _side_effect.get('peek').get('size')
            _data = _mainmem.peek(_addr, _size)
            if 'arg' not in _syscall_kwargs.keys(): _syscall_kwargs.update({'arg': []})
            _syscall_kwargs.get('arg').append(bytes(_data))
    if 'output' in _side_effect.keys():
        _register = _side_effect.get('output').get('register')
        if _register:
            setregister(_regfile, _register.get('name'), _register.get('data'))
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
        **{'side_effect': _side_effect},
        **{'syscall_kwargs': _syscall_kwargs},
        **({'shutdown': None} if 'shutdown' in _side_effect.keys() else {}),
    }
def do_csr(insn, *args, **kwargs):
    _regfile = kwargs.get('regfile')
    _operands = {
        'rs1': getregister(_regfile, insn.get('rs1')),
    }
    # HACK: csr = 0x002 is the FRM (floating point dynamic rounding mode);
    # this only handles a read from FRM by returning 0... not sure that's
    # the right thing to do, though; see: https://cv32e40p.readthedocs.io/en/latest/control_status_registers.html
    _result = {
        2: 0 # CSR = 2 means FRM
    }.get(insn.get('csr'), None)
    setregister(_regfile, insn.get('rd'), _result)
    setregister(_regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
    return {
        **insn,
        **{'operands': _operands},
        **{'result': _result},
    }

def fast(service, state, regfile, mainmem, system, N=10**100):
    logging.info('regfile : {}'.format(dir(regfile)))
    logging.info('mainmem : {}'.format(dir(mainmem)))
    logging.info('mainmem.name : {}'.format(mainmem.get('name')))
    logging.info('mainmem.fd : {}'.format(mainmem.get('fd')))
    logging.info('mainmem.config.main_memory_filename : {}'.format(mainmem.get('config').get('main_memory_filename')))
    logging.info('mainmem.config.main_memory_capacity : {}'.format(mainmem.get('config').get('main_memory_capacity')))
    logging.info('registers : {}'.format(regfile.registers))
    _opcode = {
        'LUI': do_lui,
        'AUIPC': do_auipc,
        'JAL': do_jal,
        'JALR': do_jalr,
        'BEQ': do_branch,
        'BNE': do_branch,
        'BLT': do_branch,
        'BGE': do_branch,
        'BLTU': do_branch,
        'BGEU': do_branch,
        'ADDI': do_itype,
        'SLTI': do_itype,
        'SLTIU': do_itype,
        'ADDIW': do_itype,
        'XORI': do_itype,
        'ORI': do_itype,
        'ANDI': do_itype,
        'ADD': do_rtype,
        'SUB': do_rtype,
        'XOR': do_rtype,
        'SLL': do_rtype,
        'SRL': do_rtype,
        'SRA': do_rtype,
        'SLT': do_rtype,
        'SLTU': do_rtype,
        'OR': do_rtype,
        'AND': do_rtype,
        'ADDW': do_rtype,
        'SUBW': do_rtype,
        'SLLW': do_rtype,
        'SRLW': do_rtype,
        'SRAW': do_rtype,
        'MUL': do_rtype,
        'MULH': do_rtype,
        'MULHSU': do_rtype,
        'MULHU': do_rtype,
        'DIV': do_rtype,
        'DIVU': do_rtype,
        'REM': do_rtype,
        'REMU': do_rtype,
        'MULW': do_rtype,
        'DIVW': do_rtype,
        'DIVUW': do_rtype,
        'REMW': do_rtype,
        'REMUW': do_rtype,
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
        'NOP': do_nop,
        'SLLI': do_shift,
        'SRLI': do_shift,
        'SRAI': do_shift,
        'SLLIW': do_shift,
        'SRLIW': do_shift,
        'SRAIW': do_shift,
        'ECALL': do_ecall,
        'CSRRS': do_csr,
        'CSRRSI': do_csr,
    }
    _initial_instructions_committed = state.get('instructions_committed')
    _result = None
    for _ in range(N):
        _pc = getregister(regfile, '%pc')
        _addr = int.from_bytes(_pc, 'little')
        _size = 4
        _data = mainmem.peek(_addr, _size)
        assert len(_data) == _size, 'Fetched wrong number of bytes!'
        _decoded = riscv.decode.do_decode(_data[:], 1)
        _insn = ({
            **next(iter(_decoded)),
            **{'iid': state.get('instructions_committed')},
            **{'%pc': _pc, '_pc': _addr},
            **({'function': next(filter(lambda x: int.from_bytes(_pc, 'little') >= x[0], sorted(state.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
        } if len(_decoded) else None)
        if not _insn:
            logging.info('_pc       : {}'.format(_pc))
            logging.info('_data     : {} ({})'.format(_data, len(_data)))
            logging.info('_size     : {}'.format(_size))
            logging.info('_decoded  : {}'.format(_decoded))
            break
        _result = _opcode.get(_insn.get('cmd'), do_unimplemented)(_insn, service, state, **{'regfile': regfile, 'mainmem': mainmem, 'system': system})
        logging.info('_result   : {}'.format(_result))
        state.update({'instructions_committed': 1 + state.get('instructions_committed')})
        if 'shutdown' in _result.keys(): break
    logging.info('registers : {}'.format(regfile.registers))
    logging.info('state.instructions_committed    : {}'.format(state.get('instructions_committed')))
    logging.info('_initial_instructions_committed : {}'.format(_initial_instructions_committed))
    toolbox.report_stats(service, state, 'flat', 'instructions_committed', **{'increment': state.get('instructions_committed') - _initial_instructions_committed})
    if 'shutdown' in _result.keys():
        service.tx({'info': 'ECALL {}... graceful shutdown'.format(int.from_bytes(_result.get('operands').get('syscall_num'), 'little'))})
        service.tx({'shutdown': 1 + state.get('cycle')})
        state.update({'shutdown': True})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
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
        'service': 'fastcore',
        'cycle': 0,
        'active': True,
        'running': False,
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        '%pc': None,
        'ack': True,
        'instructions_committed': 0,
        'shutdown': None,
        'objmap': None,
        'config': {
            'toolchain': '',
            'binary': '',
            'main_memory_filename': '/tmp/mainmem.raw',
            'main_memory_capacity': 2**32,
            'peek_latency_in_cycles': 500,
        },
    }
    _service = service.Service(state.get('service'), _launcher.get('host'), _launcher.get('port'))
    _regfile = regfile.SimpleRegisterFile('regfile', _launcher, _service)
    _mainmem = mainmem.SimpleMainMemory('mainmem', _launcher, _service)
    _system = riscv.syscall.linux.System()
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                if state.get('config').get('toolchain'):
                    _toolchain = state.get('config').get('toolchain')
                    _binary = state.get('binary')
                    _files = next(iter(list(os.walk(_toolchain))))[-1]
                    _objdump = next(filter(lambda x: 'objdump' in x, _files))
                    _x = subprocess.run('{} -t {}'.format(os.path.join(_toolchain, _objdump), _binary).split(), capture_output=True)
                    if not len(_x.stderr):
                        _objdump = _x.stdout.decode('ascii').split('\n')
                        _objdump = sorted(filter(lambda x: len(x), _objdump))
                        _objdump = filter(lambda x: re.search('^0', x), _objdump)
                        _objdump = map(lambda x: x.split(), _objdump)
                        state.update({'objmap': {
                            int(x[0], 16): {
                                'flags': x[1:-1],
                                'name': x[-1]
                            } for x in _objdump
                        }})
                logging.info('_mainmem.config : {}'.format(_mainmem.get('config')))
                _mainmem.boot()
            elif 'binary' == k:
                state.update({'binary': v})
            elif 'config' == k:
                logging.info('config : {}'.format(v))
                _components = {
                    'regfile': _regfile,
                    'mainmem': _mainmem,
                    'system': _system,
                    state.get('service'): state,
                }
                if v.get('service') not in _components.keys(): continue
                _target = _components.get(v.get('service'))
                _field = v.get('field')
                _val = v.get('val')
                assert _field in _target.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, v.get('service'))
                _target.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                if not state.get('shutdown'): fast(_service, state, _regfile, _mainmem, _system, 10**4)
#                _results = v.get('results')
#                _events = v.get('events')
#                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'register' == k:
                logging.debug('register : {}'.format(v))
                _cmd = v.get('cmd')
                _name = v.get('name')
                if 'set' == _cmd:
                    _regfile.update({'registers': _regfile.setregister(_regfile.get('registers'), _name, v.get('data'))})
                elif 'get' == _cmd:
                    _ret = _regfile.getregister(_regfile.get('registers'), _name)
                    _regfile.service.tx({'result': {'register': _ret}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    #_service.tx({'shutdown': None})

