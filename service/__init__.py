# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import socket
import json

class Service:
    MESSAGE_SIZE = 2**14
    def __init__(self, name, coreid, host, port):
        self.name = '[{:04}] {}'.format(coreid, name)
        self.coreid = coreid
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))
        self.tx({'name': self.name})
        self.tx({'blocking': self.s.getblocking()})
    def __del__(self):
        self.s.close()
    def rx(self):
        return json.loads(self.s.recv(self.MESSAGE_SIZE, socket.MSG_WAITALL).decode('ascii'))
    def tx(self, msg):
        # HACK: This pads all messages to be exactly self.MESSAGE_SIZE bytes.
        # HACK: It's dumb, but I want to focus on something else right now.
        _message = {
            str: lambda : json.dumps({'text': msg}),
            dict: lambda : json.dumps(msg),
        }.get(type(msg), lambda : json.dumps({'error': 'Undeliverable object'}))().encode('ascii')
        assert self.MESSAGE_SIZE >= len(_message), 'Message ({} B) too big!'.format(len(_message))
        _message += (' ' * (self.MESSAGE_SIZE - len(_message))).encode('ascii')
        self.s.send(_message)

if __name__ == '__main__':
    pass