import shlex
import os
from subprocess import check_output


def useradd(username, *args, **kwargs):
    def user_homedir():
        return os.path.join(kwargs['homedir_prefix'], username)

    kwargs = kwargs.copy()
    kwargs['args'] = '-m -r -U '
    kwargs['username'] = username
    if 'homedir_prefix' in kwargs:
        kwargs['args'] += ('-d ' + user_homedir())
    cmd = 'useradd {args} {username}'.format(**kwargs)
    return check_output(shlex.split(cmd))
