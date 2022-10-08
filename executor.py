# Copyright (C) 2021, 2022 John Haskins Jr.

import os
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

def launch(cmd, runpath, pipeline, script):
    print('cwd      : {}'.format(os.getcwd()))
    print('runpath  : {}'.format(runpath))
    print('pipeline : {}'.format(pipeline))
    print('script   : {}'.format(script))
    print('cmd      : {}'.format(cmd))
    os.mkdir(runpath)
    os.mkdir(os.path.join(runpath, 'log'))
    with open(os.path.join(runpath, 'cwd'), 'w') as fp: print(os.path.join(os.getcwd(), pipeline), file=fp)
    with open(os.path.join(runpath, 'cmdline'), 'w') as fp: print(cmd, file=fp)
    with open(os.path.join(runpath, 'script'), 'w') as fp: print(''.join(open(script, 'r').readlines()), file=fp)
    _pr = multiprocessing.Process(
        target=subprocess.run,
        args=(cmd.split(),),
        kwargs={'cwd': os.path.join(os.getcwd(), pipeline)},
        daemon=True,
    )
    _pr.start()
    return _pr
def conclude(pr, purge):
    pr.get('process').join()
    with open(os.path.join(pr.get('runpath'), 'exitcode'), 'w') as fp: print('{}'.format(pr.get('process').exitcode), file=fp)
    with open(os.path.join(pr.get('runpath'), 'sha'), 'w') as fp: print(_sha, file=fp)
    with open(os.path.join(pr.get('runpath'), 'branch'), 'w') as fp: print(_branch, file=fp)
    with open(os.path.join(pr.get('runpath'), 'exec_script'), 'w') as fp: print(args.exec_script, file=fp)
    with open(os.path.join(pr.get('runpath'), 'stats.json'), 'r') as fp: _stats = json.load(fp)
    if _mongodb: _mongodb.get('collection').insert_one({
        'sha': _sha,
        'branch': _branch,
        'exec_script': args.exec_script,
        'exitcode': pr.get('process').exitcode,
        'stats': _stats,
        'log': {
            f: open(os.path.join(pr.get('runpath'), 'log', f)).read()
            for f in {x:y for x, y, in zip(['root', 'directories', 'files'], *os.walk(os.path.join(pr.get('runpath'), 'log')))}.get('files')
        },
        'config': pr.get('config'),
        'runpath': pr.get('runpath'),
        'pipeline': pr.get('pipeline'),
        'script': pr.get('script'),
        'cmdline': pr.get('cmdline'),
        'date': int(_now.strftime('%Y%m%d')),
        'time': int(_now.strftime('%H%M%S')),
    })
    if purge and 0 == pr.get('process').exitcode: shutil.rmtree(pr.get('runpath'))

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Executor')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--purge_successful', '-P', dest='purge_successful', action='store_true', help='purge files of successful runs')
    parser.add_argument('--basepath', type=str, dest='basepath', default='/tmp', help='directory to hold runtime artifacts')
    parser.add_argument('--script', type=str, dest='script', default='main.ussim', help='script to be executed by μService-SIMulator')
    parser.add_argument('--max_cpu_utilization', type=int, dest='max_cpu_utilization', default=90, help='CPU utilization ceiling')
    parser.add_argument('--stochastic', type=float, dest='stochastic', default=1, help='Fraction (0, 1] of runs to execute')
    parser.add_argument('--mongodb', type=str, nargs=3, dest='mongodb', default=None, help='MongoDB server, database, collection')
    parser.add_argument('exec_script', help='executor script')
    args = parser.parse_args()
    assert args.stochastic > 0, '--stochastic must be greater than 0!'
    assert args.stochastic <= 1, '--stochastic must be less than or equal to 1!'
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
    _exec = json.load(open(args.exec_script, 'r'))
    _pipelines = list(_exec.keys())
    _runs = {
        p: [
            list(zip(_exec.get(p).get('config').keys(), x))
            for x in itertools.product(*_exec.get(p).get('config').values())
        ] for p in _pipelines
    }
    _processes = []
    _port = 10000
    for _p in _runs.keys():
        for _run in _runs.get(_p):
            _concluded_processes = []
            for pr in filter(lambda p: isinstance(p.get('process').exitcode, int), _processes):
                conclude(pr, args.purge_successful)
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
            _script = os.path.join(os.getcwd(), _p, args.script)
            _cmdline = ' '.join([
                'python3', os.path.join(os.getcwd(), 'launcher.py'),
                '--log', os.path.join(_runpath, 'log'),
                '--mainmem', os.path.join(_runpath, 'mainmem.raw:{}'.format(_exec.get(_p).get('mainmem'))), # HACK: hard-wired main memory size
                ('--max_cycles {}'.format(_exec.get(_p).get('max_cycles')) if 'max_cycles' in _exec.get(_p).keys() else ''),
                ('--snapshots {}'.format(_exec.get(_p).get('snapshots')) if 'snapshots' in _exec.get(_p).keys() else ''),
                ('--break_on_undefined' if 'break_on_undefined' in _exec.get(_p).keys() else ''),
                '--config', ' '.join(map(lambda r: '{}:{}'.format(*r), _run)), 'stats:output_filename:{}'.format(os.path.join(_runpath, 'stats.json')),
                '--',
                str(_port),
                _script,
                _exec.get(_p).get('command')
            ])
            f = open(_script, 'r')
            _config = filter(lambda x: 'config' in x, f.readlines())
            _config = map(lambda x: x.replace('config ', ''), _config)
            _config = map(lambda x: (x[:x.index('#')] if '#' in x else x), _config)
            _config = map(lambda x: x.strip(), _config)
            _config = filter(lambda x: not any(map(lambda r: r[0] in x, _run)), _config)
            _config = list(_config) + list(map(lambda r: '{} {}'.format(*r), _run))
            _config = map(lambda x: tuple(x.split()), _config)
            _config = map(lambda x: ((x[0], int(x[1])) if x[1].isnumeric() else x), _config) # NOTE: str.isnumeric() only accommodates integers
            _config = map(lambda x: ((x[0], True) if 'True' == x[1] else x), _config)
            _config = map(lambda x: ((x[0], False) if 'False' == x[1] else x), _config)
            _config = dict(_config)
            f.close()
            while psutil.cpu_percent(1) > args.max_cpu_utilization: pass
            _processes.append({
                'process': launch(_cmdline, _runpath, _p, _script),
                'cmdline': _cmdline,
                'runpath': _runpath,
                'pipeline': _p,
                'config': _config,
                'script': _script,
                'port': _port,
            })
    for pr in _processes: conclude(pr, args.purge_successful)