# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import subprocess
import functools

import regfile
import mainmem
import service
import toolbox
import riscv.decode
import riscv.execute
import riscv.constants
import riscv.syscall.linux

def compose(*funcs): return functools.reduce(lambda a, b: lambda x: a(b(x)), funcs, lambda x: x)

class BasicBlockCore:
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
        self.objmap = None
        self.snapshots = []
        self.cmdline = None
        self.basicblockcache = {}
        self.config = {
            'toolchain': '',
            'binary': '',
        }
        self.opcode = {
            'LUI': riscv.execute.lui,
            'AUIPC': riscv.execute.auipc,
            'JAL': riscv.execute.jal,
            'JALR': riscv.execute.jalr,
            'BEQ': riscv.execute.beq,
            'BNE': riscv.execute.bne,
            'BLT': riscv.execute.blt,
            'BGE': riscv.execute.bge,
            'BLTU': riscv.execute.bltu,
            'BGEU': riscv.execute.bgeu,
            'ADDI': riscv.execute.addi,
            'SLTI': riscv.execute.slti,
            'SLTIU': riscv.execute.sltiu,
            'ADDIW': riscv.execute.addiw,
            'XORI': riscv.execute.xori,
            'ORI': riscv.execute.ori,
            'ANDI': riscv.execute.andi,
            'ADD': riscv.execute.add,
            'SUB': riscv.execute.sub,
            'XOR': riscv.execute.xor,
            'SLL': riscv.execute.sll,
            'SRL': riscv.execute.srl,
            'SRA': riscv.execute.sra,
            'SLT': riscv.execute.slt,
            'SLTU': riscv.execute.sltu,
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
            'LD': self.mk_load('LD'),
            'LW': self.mk_load('LW'),
            'LH': self.mk_load('LH'),
            'LB': self.mk_load('LB'),
            'LWU': self.mk_load('LWU'),
            'LHU': self.mk_load('LHU'),
            'LBU': self.mk_load('LBU'),
            'SD': self.mk_store('SD'),
            'SW': self.mk_store('SW'),
            'SH': self.mk_store('SH'),
            'SB': self.mk_store('SB'),
            'NOP': lambda *args: None,
            'SLLI': riscv.execute.slli,
            'SRLI': riscv.execute.srli,
            'SRAI': riscv.execute.srai,
            'SLLIW': riscv.execute.slliw,
            'SRLIW': riscv.execute.srliw,
            'SRAIW': riscv.execute.sraiw,
            'ECALL': self.do_ecall,
            'CSRRS': self.do_csr,
            'CSRRSI': self.do_csr,
        }
        logging.info('BasicBlockCore.__init__(): self.name                    : {}'.format(self.name))
        logging.info('BasicBlockCore.__init__(): self.regfile                 : {}'.format(dir(self.regfile)))
        logging.info('BasicBlockCore.__init__(): self.mainmem                 : {}'.format(dir(self.mainmem)))
        logging.info('BasicBlockCore.__init__(): self.mainmem.name            : {}'.format(self.mainmem.get('name')))
        logging.info('BasicBlockCore.__init__(): self.mainmem.fd              : {}'.format(self.mainmem.get('fd')))
        logging.info('BasicBlockCore.__init__(): self.mainmem.config.filename : {}'.format(self.mainmem.get('config').get('filename')))
        logging.info('BasicBlockCore.__init__(): self.mainmem.config.capacity : {}'.format(self.mainmem.get('config').get('capacity')))
        logging.info('BasicBlockCore.__init__(): self.regfile.registers       : {}'.format(self.regfile.registers))
        logging.info('BasicBlockCore.__init__(): self.system                  : {}'.format(dir(self.system)))
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
    def getregister(self, regfile, reg):
        return regfile.getregister(regfile.registers, reg)
    def setregister(self, regfile, reg, val):
        regfile.registers = regfile.setregister(regfile.registers, reg, val)
    def buildbasicblock(self, pc):
        _retval = []
        _addr = int.from_bytes(pc, 'little')
        _size = 4
        while True:
            _data = self.mainmem.peek(_addr, _size, **{'coreid': self.get('coreid')})
            assert len(_data) == _size, 'Fetched wrong number of bytes!'
            _decoded = riscv.decode.do_decode(_data[:], 1)
            _insn = ({
                **next(iter(_decoded)),
                **{'%pc': pc, '_pc': _addr},
                **({'function': next(filter(lambda x: int.from_bytes(pc, 'little') >= x[0], sorted(self.get('objmap').items(), reverse=True)))[-1].get('name', '')} if self.get('objmap') else {}),
            } if len(_decoded) else None)
            if not _insn:
                logging.info('_pc       : {}'.format(pc))
                logging.info('_data     : {} ({})'.format(_data, len(_data)))
                logging.info('_size     : {}'.format(_size))
                logging.info('_decoded  : {}'.format(_decoded))
                logging.info('_retval   : {} ({})'.format(_retval, len(_retval)))
                return []
            _retval.append(functools.partial(self.do_instruction, {
                'insn': _insn,
                'op': self.opcode.get(_insn.get('cmd'), self.do_unimplemented),
            }))
            _addr += _insn.get('size')
            if _insn.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS + ['ECALL']: break
        return list(reversed(_retval))
    def execute(self, N=10**100):
        _initial_instructions_committed = state.get('instructions_committed')
        while (self.get('instructions_committed') - _initial_instructions_committed) < N:
            _pc = self.getregister(self.regfile, '%pc')
            _addr = int.from_bytes(_pc, 'little')
            if not _addr in self.basicblockcache.keys(): self.basicblockcache.update({_addr: self.buildbasicblock(_pc)})
            self.regfile = compose(*self.basicblockcache.get(_addr))(self.regfile)
            self.update({'instructions_committed': len(self.basicblockcache.get(_addr)) + self.get('instructions_committed')})
            if -1 == int.from_bytes(self.getregister(self.regfile, '%pc'), 'little', signed=True): break
        logging.info('registers : {}'.format(self.regfile.registers))
        logging.info('state.instructions_committed    : {}'.format(self.get('instructions_committed')))
        logging.info('_initial_instructions_committed : {}'.format(_initial_instructions_committed))
        _increment = self.get('instructions_committed') - _initial_instructions_committed
        toolbox.report_stats(self.service, self.state(), 'flat', 'instructions_committed', **{'increment': _increment})
        self.service.tx({'committed': _increment})
        if -1 == int.from_bytes(self.getregister(self.regfile, '%pc'), 'little', signed=True):
            self.service.tx({'info': 'Graceful shutdown...'})
            self.service.tx({'shutdown': {
                'coreid': state.get('coreid'),
            }})
            self.update({'shutdown': True})
    def do_instruction(self, nibble, regs):
        _args = ((nibble.get('insn'), regs) if nibble.get('insn').get('cmd') in riscv.constants.LOADS + riscv.constants.STORES + ['ECALL', 'CSRRS', 'CSSRSI'] else tuple(filter(
            lambda x: None != x, [
                (self.getregister(regs, '%pc') if nibble.get('insn').get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS + ['AUIPC'] else None),
                (self.getregister(regs, nibble.get('insn').get('rs1')) if 'rs1' in nibble.get('insn').keys() else None),
                (self.getregister(regs, nibble.get('insn').get('rs2')) if 'rs2' in nibble.get('insn').keys() else None),
                (nibble.get('insn').get('shamt') if 'shamt' in nibble.get('insn').keys() else None),
                (nibble.get('insn').get('imm') if 'imm' in nibble.get('insn').keys() else None),
                (nibble.get('insn').get('size') if nibble.get('insn').get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS else None),
            ]
        )))
#        logging.info('nibble.insn : {}'.format(nibble.get('insn')))
#        logging.info('_args       : {}'.format(_args))
        _result = nibble.get('op')(*_args)
        if -1 == int.from_bytes(self.getregister(regs, '%pc'), 'little', signed=True): return regs
        self.setregister(regs, '%pc', riscv.constants.integer_to_list_of_bytes(nibble.get('insn').get('size') + int.from_bytes(self.getregister(regs, '%pc'), 'little'), 64, 'little'))
        if isinstance(_result, tuple):
            if nibble.get('insn').get('cmd') in riscv.constants.BRANCHES:
                _next_pc, _taken = _result
                self.setregister(regs, '%pc', _next_pc)
            elif nibble.get('insn').get('cmd') in riscv.constants.JUMPS:
                _next_pc, _ret_pc = _result
                self.setregister(regs, nibble.get('insn').get('rd'), _ret_pc)
                self.setregister(regs, '%pc', _next_pc)
            else:
                assert False, 'Unknown tuple for _result : {}'.format(_result)
        elif isinstance(_result, list):
            self.setregister(regs, nibble.get('insn').get('rd'), _result)
        elif self.do_unimplemented == nibble.get('op'):
            pass
        elif None == _result:
            assert nibble.get('insn').get('cmd') in riscv.constants.STORES + ['NOP'], 'nibble : {}'.format(nibble)
        return regs
    def do_unimplemented(self, insn, service, state, **kwargs):
        logging.info('Unimplemented: {}'.format(state.get('pending_execute')))
        service.tx({'undefined': insn})
        return None
    def mk_load(self, cmd):
        fetch = lambda n, r: self.mainmem.peek(n.get('imm') + int.from_bytes(self.getregister(r, n.get('rs1')), 'little'), n.get('nbytes'), **{'coreid': self.get('coreid')})
        return {
            'LD': lambda n, r, *a, **k: fetch(n, r),
            'LW': lambda n, r, *a, **k: fetch(n, r) + [(0xff if ((fetch(n, r)[3] >> 7) & 0b1) else 0)] * 4,
            'LH': lambda n, r, *a, **k: fetch(n, r) + [(0xff if ((fetch(n, r)[1] >> 7) & 0b1) else 0)] * 6,
            'LB': lambda n, r, *a, **k: fetch(n, r) + [(0xff if ((fetch(n, r)[0] >> 7) & 0b1) else 0)] * 7,
            'LWU': lambda n, r, *a, **k: fetch(n, r) + [0] * 4,
            'LHU': lambda n, r, *a, **k: fetch(n, r) + [0] * 6,
            'LBU': lambda n, r, *a, **k: fetch(n, r) + [0] * 7,
        }.get(cmd)
    def mk_store(self, cmd):
        return {
            'SD': lambda n, r, *a, **k: self.mainmem.poke(n.get('imm') + int.from_bytes(self.getregister(r, n.get('rs1')), 'little'), n.get('nbytes'), self.getregister(r, n.get('rs2')), **{'coreid': self.get('coreid')}),
            'SW': lambda n, r, *a, **k: self.mainmem.poke(n.get('imm') + int.from_bytes(self.getregister(r, n.get('rs1')), 'little'), n.get('nbytes'), self.getregister(r, n.get('rs2'))[:4], **{'coreid': self.get('coreid')}),
            'SH': lambda n, r, *a, **k: self.mainmem.poke(n.get('imm') + int.from_bytes(self.getregister(r, n.get('rs1')), 'little'), n.get('nbytes'), self.getregister(r, n.get('rs2'))[:2], **{'coreid': self.get('coreid')}),
            'SB': lambda n, r, *a, **k: self.mainmem.poke(n.get('imm') + int.from_bytes(self.getregister(r, n.get('rs1')), 'little'), n.get('nbytes'), self.getregister(r, n.get('rs2'))[:1], **{'coreid': self.get('coreid')}),
        }.get(cmd)
    def do_ecall(self, insn, regs, *args, **kwargs):
        _operands = {
            'syscall_num': self.getregister(regs, 17),
            'a0': self.getregister(regs, 10),
            'a1': self.getregister(regs, 11),
            'a2': self.getregister(regs, 12),
            'a3': self.getregister(regs, 13),
            'a4': self.getregister(regs, 14),
            'a5': self.getregister(regs, 15),
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
                self.setregister(regs, _register.get('name'), _register.get('data'))
        if 'shutdown' in _side_effect.keys():
            self.setregister(regs, '%pc', riscv.constants.integer_to_list_of_bytes(-1, 64, 'little'))
        return regs
    def do_csr(self, insn, regs, *args, **kwargs):
        # HACK: csr = 0x002 is the FRM (floating point dynamic rounding mode);
        # this only handles a read from FRM by returning 0... not sure that's
        # the right thing to do, though; see: https://cv32e40p.readthedocs.io/en/latest/control_status_registers.html
        _result = {
            2: 0 # CSR = 2 means FRM
        }.get(insn.get('csr'), None)
        self.setregister(regs, insn.get('rd'), _result)
        return regs

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Basic Block Core')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('--pagesize', type=int, dest='pagesize', default=2**16, help='MMU page size in bytes')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
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
    _service = service.Service('basicblockcore', args.coreid, _launcher.get('host'), _launcher.get('port'))
    _regfile = regfile.SimpleRegisterFile('regfile', args.coreid, _launcher, _service)
    _mainmem = mainmem.SimpleMainMemory('mainmem', _launcher, args.pagesize, _service)
    _system = riscv.syscall.linux.System()
    state = BasicBlockCore('basicblockcore', args.coreid, _service, _regfile, _mainmem, _system)
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
                    state.get('name'): state,
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
                _snapshot_filename = v.get('snapshot_filename')
                _restore = _mainmem.restore(_snapshot_filename)
                _regfile.registers = _restore.get('registers')
                _regfile.update({'cycle': _restore.get('cycle')})
                _mainmem.update({'cycle': _restore.get('cycle')})
                state.update({'cycle': _restore.get('cycle')})
                state.update({'instructions_committed': _restore.get('instructions_committed')})
                logging.info('state.cycle : {}'.format(state.get('cycle')))
                logging.info('state.instructions_committed : {}'.format(state.get('instructions_committed')))
                _service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'snapshots' == k:
                state.update({'snapshots': v.get('checkpoints')})
                state.update({'cmdline': v.get('cmdline')})
            elif 'tick' == k:
                _regfile.update({'cycle': v.get('cycle')})
                _mainmem.update({'cycle': v.get('cycle')})
                state.update({'cycle': v.get('cycle')})
                _do_snapshot = 0 < len(state.get('snapshots'))
                _instruction_count = (10**5 if not len(state.get('snapshots')) else state.get('snapshots').pop(0) - state.get('instructions_committed'))
                if not state.get('shutdown'):
                    state.execute(_instruction_count)
                    if _do_snapshot: _snapshot_filename = _mainmem.snapshot({
                        'cycle': state.get('cycle'),
                        'instructions_committed': state.get('instructions_committed'),
                        'cmdline': state.get('cmdline'),
                        'registers': _regfile.registers,
                    })
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

