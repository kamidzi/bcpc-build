from os import setuid
from os import geteuid
from os import seteuid
from os import setegid
import os
from pwd import getpwnam
import contextlib
import sys

from bcpc_build.utils.vbox import get_vbox_sysprop
from bcpc_build.utils import netid_from_name
from bcpc_build.utils.credentials import env

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

    new_uid = None
    try:
        username = sys.argv[1]
        pw_ent = getpwnam(username)
        new_uid = pw_ent.pw_uid
        sys.argv.pop(1)
    except Exception as e:
        sys.exit(e)
        
    if new_uid:
        setuid(new_uid)
    #    setegid(new_uid)
    #    seteuid(new_uid)
    with env({'HOME': pw_ent.pw_dir}):
        vm_dir = get_vbox_sysprop('default_machine_folder')

    print(vm_dir)
    for label in sys.argv[1:]:
        print(label, netid_from_name(label))

