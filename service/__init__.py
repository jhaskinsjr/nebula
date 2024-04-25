# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import socket
import json
import time

#_payload = json.dumps(...)
#zlib.decompress(int(json.loads(json.dumps({
#    'cdata': int.from_bytes(
#        zlib.compress(_payload.encode('ascii')),
#        'little',
#        signed=False,
#    )
#})).get('cdata')).to_bytes(2**14, 'little')).decode('ascii')

class Service:
    MESSAGE_SIZE = 2**14
    def __init__(self, name, coreid, host=None, port=None, **kwargs):
        self.name = name
        self.coreid = coreid
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))
        self.tx({
            'name': self.name,
            'coreid': self.coreid,
            'blocking': self.s.getblocking(),
        })
    def __del__(self):
        self.s.close()
    def rx(self): return unformat(rx(self.s))
    def tx(self, msg): tx(self.s, format(msg), already_formatted=True)
def format(msg):
    # HACK: This pads all messages to be exactly self.MESSAGE_SIZE bytes.
    # HACK: It's dumb, but I want to focus on something else right now.
    _message = {
        str: lambda : json.dumps({'text': msg}),
        dict: lambda : json.dumps(msg),
    }.get(type(msg), lambda : json.dumps({'error': 'Undeliverable object'}))().encode('ascii')
    assert Service.MESSAGE_SIZE >= len(_message), 'Message ({} B) too big!'.format(len(_message))
    _message += (' ' * (Service.MESSAGE_SIZE - len(_message))).encode('ascii')
    return _message
def unformat(data): return data
def tx(s, msg, **kwargs):
    s.send(msg if kwargs.get('already_formatted') else format(msg))
def rx(s):
    _msg = s.recv(Service.MESSAGE_SIZE, socket.MSG_WAITALL)
    while not len(_msg.strip()):
        time.sleep(0.001)
        continue
    return unformat(json.loads(_msg.decode('ascii')))

if __name__ == '__main__':
    pass