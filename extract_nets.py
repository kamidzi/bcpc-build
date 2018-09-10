import json

def enumerate_nets(filename):
    with open(filename) as f:
        config = json.load(f)

        def _extract_nets():
            for host in config:
                yield from host['networks']

        return set(_extract_nets())


if __name__ == '__main__':
    print(enumerate_nets('hosts.json'))
