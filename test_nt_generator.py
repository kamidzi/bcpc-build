from os import geteuid
from pwd import getpwnam
import contextlib
import sys

from bcpc_build.net import NetworkIDGenerator
from bcpc_build.utils.vbox import get_vbox_sysprop
from bcpc_build.utils.credentials import impersonate
from bcpc_build.utils.credentials import UserContextSwitchError

# contextlib.nullcontext only in python3.7+
@contextlib.contextmanager
def nullcontext():
    try:
        yield
    finally:
        pass


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

    try:
        username = sys.argv[1]
        getpwnam(username)
        sys.argv.pop(1)
        cm = impersonate(username)
    except:
        cm = nullcontext()
        
    try:
        with cm:
            vm_dir = get_vbox_sysprop('default_machine_folder')
            print(vm_dir)
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
    except UserContextSwitchError:
        sys.exit('Failed to switch user to `{}`'.format(username))
