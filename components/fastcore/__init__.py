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

class FastCore:
    def __init__(self, name, coreid, svc, reg, mem, sys):
        self.name = name
        self.coreid = coreid
        self.service = svc
        self.regfile = reg
        self.mainmem = mem
        self.system = sys
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.instructions_committed = 0
        self.shutdown = None
        self.objmap =None
        self.config = {
            'toolchain': '',
            'binary': '',
        }
        self.opcode = {
            'LUI': self.do_lui,
            'AUIPC': self.do_auipc,
            'JAL': self.do_jal,
            'JALR': self.do_jalr,
            'BEQ': self.do_branch,
            'BNE': self.do_branch,
            'BLT': self.do_branch,
            'BGE': self.do_branch,
            'BLTU': self.do_branch,
            'BGEU': self.do_branch,
            'ADDI': self.do_itype,
            'SLTI': self.do_itype,
            'SLTIU': self.do_itype,
            'ADDIW': self.do_itype,
            'XORI': self.do_itype,
            'ORI': self.do_itype,
            'ANDI': self.do_itype,
            'ADD': self.do_rtype,
            'SUB': self.do_rtype,
            'XOR': self.do_rtype,
            'SLL': self.do_rtype,
            'SRL': self.do_rtype,
            'SRA': self.do_rtype,
            'SLT': self.do_rtype,
            'SLTU': self.do_rtype,
            'OR': self.do_rtype,
            'AND': self.do_rtype,
            'ADDW': self.do_rtype,
            'SUBW': self.do_rtype,
            'SLLW': self.do_rtype,
            'SRLW': self.do_rtype,
            'SRAW': self.do_rtype,
            'MUL': self.do_rtype,
            'MULH': self.do_rtype,
            'MULHSU': self.do_rtype,
            'MULHU': self.do_rtype,
            'DIV': self.do_rtype,
            'DIVU': self.do_rtype,
            'REM': self.do_rtype,
            'REMU': self.do_rtype,
            'MULW': self.do_rtype,
            'DIVW': self.do_rtype,
            'DIVUW': self.do_rtype,
            'REMW': self.do_rtype,
            'REMUW': self.do_rtype,
            'LD': self.do_load,
            'LW': self.do_load,
            'LH': self.do_load,
            'LB': self.do_load,
            'LWU': self.do_load,
            'LHU': self.do_load,
            'LBU': self.do_load,
            'SD': self.do_store,
            'SW': self.do_store,
            'SH': self.do_store,
            'SB': self.do_store,
            'NOP': self.do_nop,
            'SLLI': self.do_shift,
            'SRLI': self.do_shift,
            'SRAI': self.do_shift,
            'SLLIW': self.do_shift,
            'SRLIW': self.do_shift,
            'SRAIW': self.do_shift,
            'ECALL': self.do_ecall,
            'CSRRS': self.do_csr,
            'CSRRSI': self.do_csr,
        }
        logging.info('FastCore.__init__(): self.name                    : {}'.format(self.name))
        logging.info('FastCore.__init__(): self.regfile                 : {}'.format(dir(self.regfile)))
        logging.info('FastCore.__init__(): self.mainmem                 : {}'.format(dir(self.mainmem)))
        logging.info('FastCore.__init__(): self.mainmem.name            : {}'.format(self.mainmem.get('name')))
        logging.info('FastCore.__init__(): self.mainmem.fd              : {}'.format(self.mainmem.get('fd')))
        logging.info('FastCore.__init__(): self.mainmem.config.filename : {}'.format(self.mainmem.get('config').get('filename')))
        logging.info('FastCore.__init__(): self.mainmem.config.capacity : {}'.format(self.mainmem.get('config').get('capacity')))
        logging.info('FastCore.__init__(): self.registers               : {}'.format(self.regfile.registers))
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
    def execute(self, N=10**100):
        _initial_instructions_committed = state.get('instructions_committed')
        _result = None
        for _ in range(N):
            _pc = self.getregister(self.regfile, '%pc')
            _addr = int.from_bytes(_pc, 'little')
            _size = 4
            _data = self.mainmem.peek(_addr, _size, **{'coreid': self.get('coreid')})
            assert len(_data) == _size, 'Fetched wrong number of bytes!'
            _decoded = riscv.decode.do_decode(_data[:], 1)
            _insn = ({
                **next(iter(_decoded)),
                **{'iid': state.get('instructions_committed')},
                **{'%pc': _pc, '_pc': _addr},
                **({'function': next(filter(lambda x: int.from_bytes(_pc, 'little') >= x[0], sorted(self.get('objmap').items(), reverse=True)))[-1].get('name', '')} if self.get('objmap') else {}),
            } if len(_decoded) else None)
            if not _insn:
                logging.info('_pc       : {}'.format(_pc))
                logging.info('_data     : {} ({})'.format(_data, len(_data)))
                logging.info('_size     : {}'.format(_size))
                logging.info('_decoded  : {}'.format(_decoded))
                break
            _result = self.opcode.get(_insn.get('cmd'), self.do_unimplemented)(_insn, self.service, self.state())
            logging.info('_result   : {}'.format(_result))
            self.update({'instructions_committed': 1 + self.get('instructions_committed')})
            if 'shutdown' in _result.keys(): break
        logging.info('registers : {}'.format(self.regfile.registers))
        logging.info('state.instructions_committed    : {}'.format(self.get('instructions_committed')))
        logging.info('_initial_instructions_committed : {}'.format(_initial_instructions_committed))
        _increment = self.get('instructions_committed') - _initial_instructions_committed
        toolbox.report_stats(self.service, self.state(), 'flat', 'instructions_committed', **{'increment': _increment})
        self.service.tx({'committed': _increment})
        if 'shutdown' in _result.keys():
            self.service.tx({'info': 'ECALL {}... graceful shutdown'.format(int.from_bytes(_result.get('operands').get('syscall_num'), 'little'))})
            self.service.tx({'shutdown': {
                'coreid': state.get('coreid'),
            }})
            self.update({'shutdown': True})
    def getregister(self, regfile, reg):
        return regfile.getregister(regfile.registers, reg)
    def setregister(self, regfile, reg, val):
        regfile.registers = regfile.setregister(regfile.registers, reg, val)
    def do_unimplemented(self, insn, service, state, **kwargs):
        logging.info('Unimplemented: {}'.format(state.get('pending_execute')))
        service.tx({'undefined': insn})
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return insn
    def do_lui(self, insn, *args, **kwargs):
        self.setregister(self.regfile, insn.get('rd'), riscv.execute.lui(insn.get('imm')))
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return insn
    def do_auipc(self, insn, *args, **kwargs):
        self.setregister(self.regfile, insn.get('rd'), riscv.execute.auipc(insn.get('%pc'), insn.get('imm')))
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return insn
    def do_jal(self, insn, *args, **kwargs):
        _next_pc, _ret_pc = riscv.execute.jal(insn.get('%pc'), insn.get('imm'), insn.get('size'))
        self.setregister(self.regfile, '%pc', _next_pc)
        self.setregister(self.regfile, insn.get('rd'), _ret_pc)
        return {
            **insn,
            **{'next_pc': _next_pc},
            **{'ret_pc': _ret_pc},
        }
    def do_jalr(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
        }
        _next_pc, _ret_pc = riscv.execute.jalr(insn.get('%pc'), insn.get('imm'), _operands.get('rs1'), insn.get('size'))
        self.setregister(self.regfile, '%pc', _next_pc)
        self.setregister(self.regfile, insn.get('rd'), _ret_pc)
        return {
            **insn,
            **{'operands': _operands},
            **{'next_pc': _next_pc},
            **{'ret_pc': _ret_pc},
        }
    def do_branch(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
            'rs2': self.getregister(self.regfile, insn.get('rs2')),
        }
        _next_pc, _taken = {
            'BEQ': riscv.execute.beq,
            'BNE': riscv.execute.bne,
            'BLT': riscv.execute.blt,
            'BGE': riscv.execute.bge,
            'BLTU': riscv.execute.bltu,
            'BGEU': riscv.execute.bgeu,
        }.get(insn.get('cmd'))(insn.get('%pc'), _operands.get('rs1'), _operands.get('rs2'), insn.get('imm'), insn.get('size'))
        self.setregister(self.regfile, '%pc', _next_pc)
        return {
            **insn,
            **{'operands': _operands},
            **{'next_pc': _next_pc},
            **{'taken': _taken},
        }
    def do_itype(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
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
        self.setregister(self.regfile, insn.get('rd'), _result)
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
            **{'result': _result},
        }
    def do_rtype(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
            'rs2': self.getregister(self.regfile, insn.get('rs2')),
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
        self.setregister(self.regfile, insn.get('rd'), _result)
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
            **{'result': _result},
        }
    def do_load(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
        }
        _addr = insn.get('imm') + int.from_bytes(_operands.get('rs1'), 'little')
        _fetched  = self.mainmem.peek(_addr, insn.get('nbytes'), **{'coreid': self.get('coreid')})
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
        self.setregister(self.regfile, insn.get('rd'), _data)
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
            **{'data': _data},
        }
    def do_store(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
            'rs2': self.getregister(self.regfile, insn.get('rs2')),
        }
        _data = _operands.get('rs2')
        _data = {
            'SD': _data,
            'SW': _data[:4],
            'SH': _data[:2],
            'SB': _data[:1],
        }.get(insn.get('cmd'))
        _addr = insn.get('imm') + int.from_bytes(_operands.get('rs1'), 'little')
        self.mainmem.poke(_addr, insn.get('nbytes'), _data, **{'coreid': self.get('coreid')})
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
        }
    def do_nop(self, insn, *args, **kwargs):
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return insn
    def do_shift(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
        }
        _result = {
            'SLLI': riscv.execute.slli,
            'SRLI': riscv.execute.srli,
            'SRAI': riscv.execute.srai,
            'SLLIW': riscv.execute.slliw,
            'SRLIW': riscv.execute.srliw,
            'SRAIW': riscv.execute.sraiw,
        }.get(insn.get('cmd'))(_operands.get('rs1'), insn.get('shamt'))
        self.setregister(self.regfile, insn.get('rd'), _result)
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
            **{'result': _result},
        }
    def do_ecall(self, insn, *args, **kwargs):
        # FIXME: actually DO the ECALL
        _operands = {
            'syscall_num': self.getregister(self.regfile, 17),
            'a0': self.getregister(self.regfile, 10),
            'a1': self.getregister(self.regfile, 11),
            'a2': self.getregister(self.regfile, 12),
            'a3': self.getregister(self.regfile, 13),
            'a4': self.getregister(self.regfile, 14),
            'a5': self.getregister(self.regfile, 15),
        }
        _side_effect = {}
        _syscall_kwargs = {}
        while not _side_effect.get('done'):
            _side_effect = self.system.do_syscall(
                _operands.get('syscall_num'),
                _operands.get('a0'), _operands.get('a1'), _operands.get('a2'), _operands.get('a3'), _operands.get('a4'), _operands.get('a5'), **{
                    **_syscall_kwargs,
                    **{'cycle': insn.get('iid')},
                }
            )
            if 'poke' in _side_effect.keys():
                _addr = int.from_bytes(_side_effect.get('poke').get('addr'), 'little')
                _data = _side_effect.get('poke').get('data')
                self.mainmem.poke(_addr, len(_data), _data, **{'coreid': self.get('coreid')})
            if 'peek' in _side_effect.keys():
                _addr = _side_effect.get('peek').get('addr')
                _size = _side_effect.get('peek').get('size')
                _data = self.mainmem.peek(_addr, _size, **{'coreid': self.get('coreid')})
                if 'arg' not in _syscall_kwargs.keys(): _syscall_kwargs.update({'arg': []})
                _syscall_kwargs.get('arg').append(bytes(_data))
        if 'output' in _side_effect.keys():
            _register = _side_effect.get('output').get('register')
            if _register:
                self.setregister(self.regfile, _register.get('name'), _register.get('data'))
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
            **{'side_effect': _side_effect},
            **{'syscall_kwargs': _syscall_kwargs},
            **({'shutdown': None} if 'shutdown' in _side_effect.keys() else {}),
        }
    def do_csr(self, insn, *args, **kwargs):
        _operands = {
            'rs1': self.getregister(self.regfile, insn.get('rs1')),
        }
        # HACK: csr = 0x002 is the FRM (floating point dynamic rounding mode);
        # this only handles a read from FRM by returning 0... not sure that's
        # the right thing to do, though; see: https://cv32e40p.readthedocs.io/en/latest/control_status_registers.html
        _result = {
            2: 0 # CSR = 2 means FRM
        }.get(insn.get('csr'), None)
        self.setregister(self.regfile, insn.get('rd'), _result)
        self.setregister(self.regfile, '%pc', riscv.constants.integer_to_list_of_bytes(int.from_bytes(insn.get('%pc'), 'little') + insn.get('size'), 64, 'little'))
        return {
            **insn,
            **{'operands': _operands},
            **{'result': _result},
        }

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('--pagesize', type=int, dest='pagesize', default=2**16, help='MMU page size in bytes')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    assert not os.path.isfile(args.log), '--log must point to directory, not file'
    while not os.path.isdir(args.log):
        try:
            os.makedirs(args.log, exist_ok=True)
        except:
            time.sleep(0.1)
    logging.basicConfig(
        filename=os.path.join(args.log, '{:04}_{}.log'.format(args.coreid, os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    _service = service.Service('fastcore', args.coreid, _launcher.get('host'), _launcher.get('port'))
    _regfile = regfile.SimpleRegisterFile('regfile', args.coreid, _launcher, _service)
    _mainmem = mainmem.SimpleMainMemory('mainmem', _launcher, args.pagesize, _service)
    _system = riscv.syscall.linux.System()
    state = FastCore('fastcore', args.coreid, _service, _regfile, _mainmem, _system)
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
            elif 'loadbin' == k:
                logging.info('loadbin : {}'.format(v))
                _coreid = v.get('coreid')
                _start_symbol = v.get('start_symbol')
                _sp = v.get('sp')
                _pc = v.get('pc')
                _binary = v.get('binary')
                _args = v.get('args')
                _mainmem.boot()
                _mainmem.loadbin(_coreid, _start_symbol, _sp, _pc, _binary, *_args)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                logging.info('restore : {}'.format(v))
                _regfile.update({'cycle': v.get('cycle')})
                _mainmem.update({'cycle': v.get('cycle')})
                state.update({'cycle': v.get('cycle')})
                state.update({'instructions_committed': v.get('instructions_committed')})
                _snapshot_filename = v.get('snapshot_filename')
                _addr = v.get('addr')
                _mainmem.restore(_snapshot_filename, _addr)
                _regfile.restore(_snapshot_filename, _addr)
                _service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'tick' == k:
                _regfile.update({'cycle': v.get('cycle')})
                _mainmem.update({'cycle': v.get('cycle')})
                state.update({'cycle': v.get('cycle')})
                if v.get('snapshot'):
                    logging.info('tick.v : {}'.format(v))
                    _addr = v.get('snapshot').get('addr')
                    _data = v.get('snapshot').get('data')
                    _snapshot_filename = _mainmem.snapshot(_addr, _data)
                    _regfile.snapshot(_addr, _snapshot_filename)
                if not state.get('shutdown'): state.execute(10**5)
#                _results = v.get('results')
#                _events = v.get('events')
#                do_tick(_service, state, _results, _events)
            elif 'register' == k:
                logging.info('register : {}'.format(v))
                if not state.get('coreid') == v.get('coreid'): continue
                _cmd = v.get('cmd')
                _name = v.get('name')
                if 'set' == _cmd:
                    _regfile.update({'registers': _regfile.setregister(_regfile.get('registers'), _name, v.get('data'))})
                elif 'get' == _cmd:
                    _ret = _regfile.getregister(_regfile.get('registers'), _name)
                    _regfile.service.tx({'result': {'register': _ret}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})

