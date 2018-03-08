import shlex
import os
import signal
import psutil
import logging
from subprocess import check_output


def userdel(username, *args, **kwargs):
    kwargs = kwargs.copy()
    kwargs['args'] = '-r -f '
    kwargs['username'] = username
    cmd = 'userdel {args} {username}'.format(**kwargs)
    return check_output(shlex.split(cmd))

def useradd(username, *args, **kwargs):
    def user_homedir():
        return os.path.join(kwargs['homedir_prefix'], username)

    kwargs = kwargs.copy()
    kwargs['args'] = '-m -r -U '
    kwargs['username'] = username
    if 'shell' in kwargs:
        kwargs['args'] += ('-s %s ' % kwargs.pop('shell'))
    if 'homedir_prefix' in kwargs:
        kwargs['args'] += ('-d ' + user_homedir())
    cmd = 'useradd {args} {username}'.format(**kwargs)
    return check_output(shlex.split(cmd))


logger = logging.getLogger(__name__)
# https://psutil.readthedocs.io/en/latest/#kill-process-tree
def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callaback function which is
    called as soon as a child terminates.
    """
    if pid == os.getpid():
        raise RuntimeError("I refuse to kill myself")
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        if include_parent:
            children.append(parent)
        for p in children:
            p.send_signal(sig)
        gone, alive = psutil.wait_procs(children, timeout=timeout,
                                        callback=on_terminate)
        if alive:
            # send SIGKILL
            for p in alive:
                logger.warn("process {} survived SIGTERM; trying SIGKILL" % p)
                p.kill()
            gone, alive = psutil.wait_procs(alive, timeout=timeout, callback=on_terminate)
            if alive:
                # give up
                for p in alive:
                    logger.error("process {} survived SIGKILL; giving up" % p)
        return (gone, alive)
    except psutil.NoSuchProcess as e:
        return (None, None)
