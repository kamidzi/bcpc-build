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
from bcpc_build.utils.credentials import impersonated_thread

# contextlib.nullcontext only in python3.7+
@contextlib.contextmanager
def nullcontext():
    try:
        yield
    finally:
        pass


if __name__ == '__main__':
    try:
        username = sys.argv[1]
        sys.argv.pop(1)
    except Exception as e:
        sys.exit(e)
        
    def do_work():
        vm_dir = get_vbox_sysprop('default_machine_folder')
        print(vm_dir)
        for label in sys.argv[1:]:
            print(label, netid_from_name(label))

    impersonated_thread(username, do_work)
