import service

def report_stats(service, state, type, name, data=None):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'stats': {
            **{
                'service': state.get('service'),
                'type': type,
                'name': name,
            },
            **({'data': data} if None != data else {}),
        },
    }})