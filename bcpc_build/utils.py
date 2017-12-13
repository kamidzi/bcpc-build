import shlex
import os
from subprocess import check_output

HOME = '/var/lib'


def useradd(username, *args, **kwargs):
    def user_homedir():
        return os.path.join(HOME, username)

    kwargs = kwargs.copy()
    def_args = '-m -r -U '
    kwargs['username'] = username
    kwargs['args'] = def_args + '-d ' + user_homedir()
    cmd = 'useradd {args} {username}'.format(**kwargs)
    return check_output(shlex.split(cmd))
