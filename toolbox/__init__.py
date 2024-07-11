# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import service

def report_stats(service, state, type, name, data=None, **kwargs):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid', -1),
        'stats': {
            **{
                'service': state.get('service'),
                'type': type,
                'name': name,
            },
            **({'data': data} if None != data else {}),
            **({'kwargs': kwargs} if len(kwargs.keys()) else {}),
        },
    }})
def report_stats_from_dict(service, state, data):
    for n, d in data.items():
        if isinstance(d, dict):
            report_stats(service, state, 'dict', n, d)
        elif isinstance(d, int) or isinstance(d, float):
            report_stats(service, state, 'flat', n, **{'increment': d})