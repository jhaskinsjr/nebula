import os
import sys
import json
import argparse
import uuid
import itertools
import pprint
import psutil
import multiprocessing
import subprocess
import datetime
import pymongo

def launch(cmd, runpath, pipeline, script):
    print('cwd      : {}'.format(os.getcwd()))
    print('runpath  : {}'.format(runpath))
    print('pipeline : {}'.format(pipeline))
    print('script   : {}'.format(script))
    print('cmd      : {}'.format(cmd))
    os.mkdir(runpath)
    os.mkdir(os.path.join(runpath, 'log'))
#    subprocess.run('cp {} {}'.format(script, os.path.join(runpath, 'script')).split())
#    print(cmd, file=open(os.path.join(runpath, 'cmdline'), 'w'))
#    print(pipeline, file=open(os.path.join(runpath, 'pipeline'), 'w'))
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

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Executor')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('--basepath', type=str, dest='basepath', default='/tmp', help='directory to hold runtime artifacts')
    parser.add_argument('--script', type=str, dest='script', default='main.ussim', help='script to be executed by μService-SIMulator')
    parser.add_argument('--max_cpu_utilization', type=int, dest='max_cpu_utilization', default=90, help='CPU utilization ceiling')
    parser.add_argument('--mongodb', type=str, nargs=3, dest='mongodb', default=None, help='MongoDB server, database, collection')
    parser.add_argument('exec_script', help='executor script')
    args = parser.parse_args()
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
            list(zip(_exec.get('pipelines/oroblanco').get('config').keys(), x))
            for x in itertools.product(*_exec.get('pipelines/oroblanco').get('config').values())
        ] for p in _pipelines
    }
#    pprint.pprint(_runs)
#    sys.exit(0)
    _processes = []
    _port = 10000
    for _p in _runs.keys():
        for _run in _runs.get(_p):
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
#            print(_config)
            f.close()
            while psutil.cpu_percent(1) > args.max_cpu_utilization: pass
#            print(_cmdline)
            _processes.append({
                'process': launch(_cmdline, _runpath, _p, _script),
                'cmdline': _cmdline,
                'runpath': _runpath,
                'pipeline': _p,
                'config': _config,
                'script': _script,
            })
            _port += 1
    for pr in _processes:
        pr.get('process').join()
        with open(os.path.join(pr.get('runpath'), 'exitcode'), 'w') as fp: print('{}'.format(pr.get('process').exitcode), file=fp)
        with open(os.path.join(pr.get('runpath'), 'sha'), 'w') as fp: print(_sha, file=fp)
        with open(os.path.join(pr.get('runpath'), 'branch'), 'w') as fp: print(_branch, file=fp)
        with open(os.path.join(pr.get('runpath'), 'stats.json'), 'r') as fp: _stats = json.load(fp)
        if _mongodb: _mongodb.get('collection').insert_one({
            'sha': _sha,
            'branch': _branch,
            'exitcode': pr.get('process').exitcode,
            'stats': _stats,
            'config': pr.get('config'),
            'runpath': pr.get('runpath'),
            'pipeline': pr.get('pipeline'),
            'script': pr.get('script'),
            'cmdline': pr.get('cmdline'),
            'date': int(_now.strftime('%Y%m%d')),
            'time': int(_now.strftime('%H%M%S')),
        })
#        if _mongodb: _mongodb.get('collection').insert_one()
#        pprint.pprint(_document)
#    [pr.join() for pr in _processes]