# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import re
import os
import sys
import json
import argparse
import random
import uuid
import itertools
import psutil
import shutil
import multiprocessing
import subprocess
import datetime
import pymongo
import time

def go(*args, **kwargs):
    try:
        _runpath = kwargs.pop('runpath')
        _run = subprocess.run(*args, **kwargs)
        with open(os.path.join(_runpath, 'stdout'), 'w') as fp: print(_run.stdout.decode('ascii'), file=fp)
        with open(os.path.join(_runpath, 'stderr'), 'w') as fp: print(_run.stderr.decode('ascii'), file=fp)
    except Exception as ex:
        print('go(): e : {}'.format(ex))
def launch(cmd, runpath, pipeline, script, **kwargs):
#    print('cwd      : {}'.format(os.getcwd()))
#    print('runpath  : {}'.format(runpath))
#    print('pipeline : {}'.format(pipeline))
#    print('script   : {}'.format(script))
#    print('cmd      : {}'.format(cmd))
#    print('kwargs   : {}'.format(kwargs))
    _timeout = kwargs.get('timeout')
    os.mkdir(runpath)
    os.mkdir(os.path.join(runpath, 'log'))
    with open(os.path.join(runpath, 'cwd'), 'w') as fp: print(os.path.join(os.getcwd(), pipeline), file=fp)
    with open(os.path.join(runpath, 'cmdline'), 'w') as fp: print(cmd, file=fp)
    with open(os.path.join(runpath, 'script'), 'w') as fp: print(''.join(open(script, 'r').readlines()), file=fp)
    _pr = multiprocessing.Process(
        target=go,
        args=(cmd.split(),),
        kwargs={'cwd': os.path.join(os.getcwd(), pipeline), 'capture_output': True, 'timeout': _timeout, 'runpath': runpath},
        daemon=True,
    )
    _pr.start()
    return _pr
def conclude(pr, purge, sha, branch, now):
    pr.get('process').join()
    try:
        _stats = None
        _stdout = None
        _stderr = None
        with open(os.path.join(pr.get('runpath'), 'exitcode'), 'w') as fp: print('{}'.format(pr.get('process').exitcode), file=fp)
        with open(os.path.join(pr.get('runpath'), 'sha'), 'w') as fp: print(sha, file=fp)
        with open(os.path.join(pr.get('runpath'), 'branch'), 'w') as fp: print(branch, file=fp)
        with open(os.path.join(pr.get('runpath'), 'exec_script'), 'w') as fp: print(pr.get('exec_script'), file=fp)
        if os.path.exists(os.path.join(pr.get('runpath'), 'stats.json')): _stats = json.load(open(os.path.join(pr.get('runpath'), 'stats.json')))
        if os.path.exists(os.path.join(pr.get('runpath'), 'stdout')): _stdout = '\n'.join(open(os.path.join(pr.get('runpath'), 'stdout'), 'r').readlines())
        if os.path.exists(os.path.join(pr.get('runpath'), 'stderr')): _stderr = '\n'.join(open(os.path.join(pr.get('runpath'), 'stderr'), 'r').readlines())
        if _mongodb: _mongodb.get('collection').insert_one({
            'sha': sha,
            'branch': branch,
            'exec_script': pr.get('exec_script'),
            'exitcode': pr.get('process').exitcode,
            'stats': (_stats if _stats else ''),
# XXX: MongoDB's maximum document size is only 16MB
#      so I'm temporarily disabling storing the launcher.py.log file
#      until I have a workaround
            'log': {
                f: open(os.path.join(pr.get('runpath'), 'log', f)).read()
                for f in filter(lambda a: 'launcher.py' not in a and '0000_core.py' not in a, {x:y for x, y, in zip(['root', 'directories', 'files'], *os.walk(os.path.join(pr.get('runpath'), 'log')))}.get('files'))
            },
            'config': pr.get('config'),
            'runpath': pr.get('runpath'),
            'pipeline': pr.get('pipeline'),
            'script': pr.get('script'),
            'cmdline': pr.get('cmdline'),
            'stdout': (_stdout if _stdout else ''),
            'stderr': (_stderr if _stderr else ''),
            'date': int(now.strftime('%Y%m%d')),
            'time': int(now.strftime('%H%M%S')),
        })
        if purge and 0 == pr.get('process').exitcode: shutil.rmtree(pr.get('runpath'))
    except Exception as ex:
        print('conclude(): e : {}'.format(ex))
def do_exec_script(exec_script, sha, branch, now, **kwargs):
    _exec = json.load(open(exec_script, 'r'))
    _pipelines = list(_exec.keys())
    _runs = {
        p: [
            list(zip(_exec.get(p).get('config').keys(), x))
            for x in itertools.product(*_exec.get(p).get('config').values())
        ] for p in _pipelines
    }
    if 'include' in kwargs.keys():_runs = {k:_runs.get(k) for k in filter(lambda x: any(map(lambda y: re.search(y, x), kwargs.get('include'))), _runs.keys())}
    if 'exclude' in kwargs.keys():_runs = {k:_runs.get(k) for k in filter(lambda x: not any(map(lambda y: re.search(y, x), kwargs.get('exclude'))), _runs.keys())}
    if args.debug: print('_runs : {}'.format(_runs))
    if args.debug: print('_exec : {}'.format(_exec))
    _port = globals().get('port', 10000)
    _processes = []
    for _p in _runs.keys():
        for _run in _runs.get(_p):
            _concluded_processes = []
            for pr in filter(lambda p: isinstance(p.get('process').exitcode, int), _processes):
                conclude(pr, args.purge_successful, sha, branch, now)
                _concluded_processes.append(pr)
            for pr in _concluded_processes: _processes.remove(pr)
            if random.uniform(0, 1) > args.stochastic: continue
            _port += 1
            _port %= 2**16
            _port += (0 if _port else 10000) # NOTE: UNIX/Linux TCP ports range from 0 to 2**16
                                             #       There are a bunch of important ports below
                                             #       10000. I don't feel like learning them, so
                                             #       I'll just start doling them out beginning
                                             #       at 10000.
            _still_running = filter(lambda p: not isinstance(p.get('process').exitcode, int), _processes)
            while len(list(_still_running)) == 2**16 - 10000: time.sleep(1)
            _runpath = os.path.join(args.basepath, str(uuid.uuid4()))
            _script = os.path.join(os.getcwd(), _p, _exec.get(_p).get('script'))
            _command = _exec.get(_p).get('command')
            _restore = _exec.get(_p).get('restore')
            _service = _exec.get(_p).get('service')
            assert not (_command and _restore), 'Cannot give both a command and a snapshot to restore!'
            assert _command or _restore, 'Must specify either a command or a snapshot to restore!'
            _cmdline = ' '.join([
                'python3', os.path.join(os.getcwd(), 'launcher.py'),
                ('-D' if args.debug else ''),
                '--log', os.path.join(_runpath, 'log'),
                '--service',
                    ':'.join([os.path.join(os.getcwd(), 'toolbox', 'stats.py'), 'localhost', '22', '-1', '-1', '"--output_filename={}"'.format(os.path.join(_runpath, 'stats.json'))]),
                    (' '.join(_service) if _service else ''),
#                #':'.join([os.path.join('implementation', 'mainmem.py'), 'localhost', '-1']),
                ('--max_cycles {}'.format(_exec.get(_p).get('max_cycles')) if 'max_cycles' in _exec.get(_p).keys() else ''),
                ('--max_instructions {}'.format(_exec.get(_p).get('max_instructions')) if 'max_instructions' in _exec.get(_p).keys() else ''),
                ('--snapshots {}'.format(_exec.get(_p).get('snapshots')) if 'snapshots' in _exec.get(_p).keys() else ''),
                ('--break_on_undefined' if 'break_on_undefined' in _exec.get(_p).keys() else ''),
                '--config', #'stats:output_filename:{}'.format(os.path.join(_runpath, 'stats.json')),
                    'mainmem:filename:{}'.format(os.path.join(_runpath, 'mainmem.raw')), ' '.join(map(lambda r: '{}:{}'.format(*r), _run)),
                ('--restore {}'.format(os.path.join(os.getcwd(), _p, _restore)) if _restore else ''),
                '--',
                str(_port),
                _script,
                (_command if _command else '')
            ])
            f = open(_script, 'r')
            _config = filter(lambda x: 'config' in x, f.readlines())
            _config = map(lambda x: x.replace('config ', ''), _config)
            _config = map(lambda x: (x[:x.index('#')] if '#' in x else x), _config)
            _config = filter(lambda x: len(x), _config)
            _config = map(lambda x: x.strip(), _config)
            _config = filter(lambda x: not any(map(lambda r: r[0] in x, _run)), _config)
            _config = list(_config) + list(map(lambda r: '{} {}'.format(*r), _run))
            _config = map(lambda x: tuple(x.split()), _config)
            _config = map(lambda x: ((x[0], int(x[1])) if x[1].isnumeric() else x), _config) # NOTE: str.isnumeric() only accommodates integers
            _config = map(lambda x: ((x[0], True) if 'True' == x[1] else x), _config)
            _config = map(lambda x: ((x[0], False) if 'False' == x[1] else x), _config)
            _config = dict(_config)
            f.close()
            while psutil.cpu_percent(interval=5) > args.max_cpu_utilization: pass
            _processes.append({
                'process': launch(_cmdline, _runpath, _p, _script, timeout=args.timeout),
                'cmdline': _cmdline,
                'runpath': _runpath,
                'pipeline': _p,
                'config': _config,
                'script': _script,
                'exec_script': exec_script,
                'port': _port,
            })
    globals().update({'port': _port})
    return _processes

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Executor')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--purge_successful', '-P', dest='purge_successful', action='store_true', help='purge files of successful runs')
    parser.add_argument('--basepath', type=str, dest='basepath', default='/tmp', help='directory to hold runtime artifacts')
    parser.add_argument('--max_cpu_utilization', type=int, dest='max_cpu_utilization', default=90, help='CPU utilization ceiling')
    parser.add_argument('--stochastic', type=float, dest='stochastic', default=1, help='Fraction (0, 1] of runs to execute')
    parser.add_argument('--timeout', type=int, dest='timeout', default=None, help='Time (in seconds) before forceful task termination')
    parser.add_argument('--mongodb', type=str, nargs=3, dest='mongodb', default=None, help='MongoDB server, database, collection')
    parser.add_argument('--include', type=str, nargs='+', dest='include', help='pipelines to simulate')
    parser.add_argument('--exclude', type=str, nargs='+', dest='exclude', help='pipelines to NOT simulate')
    parser.add_argument('exec_script', nargs='+', help='executor script')
    args = parser.parse_args()
    assert args.stochastic > 0, '--stochastic must be greater than 0!'
    assert args.stochastic <= 1, '--stochastic must be less than or equal to 1!'
    assert not (None != args.include and None != args.exclude), 'Cannot use both --include and --exclude!'
    assert all(map(lambda x: os.path.exists(x), args.exec_script)), 'Cannot open one or more executor scripts!'
    _mongodb = None
    if args.mongodb:
        _mongodb = {
            'client': pymongo.MongoClient(args.mongodb[0]),
        }
        _mongodb.update({'db': _mongodb.get('client')[args.mongodb[1]]})
        _mongodb.update({'collection': _mongodb.get('db')[args.mongodb[2]]})
    _sha = subprocess.run('git rev-parse HEAD'.split(), capture_output=True).stdout.decode('ascii').strip()
    _branch = subprocess.run('git rev-parse --abbrev-ref HEAD'.split(), capture_output=True).stdout.decode('ascii').strip()
    _now = datetime.datetime.now()
    _processes = sum(map(lambda x: do_exec_script(x, _sha, _branch, _now, **{
        **({'include': args.include} if args.include else {}),
        **({'exclude': args.exclude} if args.exclude else {}),
    }), args.exec_script), [])
    for pr in _processes:
        try:
            conclude(pr, args.purge_successful, _sha, _branch, _now)
        except:
            pass