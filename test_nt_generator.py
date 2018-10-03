from os import geteuid
import sys

from bcpc_build.net import NetworkIDGenerator
from bcpc_build.utils.vbox import get_vbox_sysprop

if __name__ == '__main__':
# def generate_network_name(label)
#   @vmdir ||=  get_virtualbox_property('default_machine_folder')
#   mapping = {
#     label: label,
#     uid: Process.euid,
#     virtualbox_vm_dir: @vmdir,
#   }
#   @g ||= NetworkIDGenerator.new
#   id = @g.generate_id mapping
#   [label, id].join('-')
# end

    vm_dir = get_vbox_sysprop('default_machine_folder')
    uid = geteuid() 
    for label in sys.argv[1:]:
        mapping = dict(
            label=label,
            uid=uid,
            virtualbox_vm_dir=vm_dir
        )
        name = '{}-{}'.format(
            label, NetworkIDGenerator.generate_id(mapping)
        )
        print('{}: {}'.format(label, name))
