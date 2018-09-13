from bcpc_build.unit import ConfigFile
import tempfile
import os
import yaml

contents = [
 {'cpus': 1,
  'memory': 512,
  'name': 'spine1',
  'networks': ['spine1leaf1', 'spine1leaf2', 'spine1leaf3']},
 {'cpus': 1,
  'memory': 512,
  'name': 'leaf1',
  'networks': ['spine1leaf1', 'spine2leaf1', 'management1', 'storage1']},
 {'cpus': 1,
  'memory': 512,
  'name': 'leaf2',
  'networks': ['spine1leaf2', 'spine2leaf2', 'management2', 'storage2']},
 {'cpus': 1,
  'memory': 512,
  'name': 'leaf3',
  'networks': ['spine1leaf3', 'spine2leaf3', 'management3', 'storage3']}
 ]


def inc_cpu(contents):
    for host in contents:
        n = host['cpus']
        host['cpus'] = n + 1 
    return contents

def half_mem(contents):
    for host in contents:
        n = host['memory']
        host['memory'] = n//2
    return contents

updates = [inc_cpu, half_mem]
from pprint import pprint
with tempfile.NamedTemporaryFile(mode='w+') as f:
    yaml.dump(contents, f)
    conf = ConfigFile(os.path.basename(f.name), f.name)

    for state in conf.transform(*updates):
        print(state)

with conf.edit() as contents:
    contents.pop()

# This will fail because file is gone now
# conf.refresh()

pprint(conf.contents)
