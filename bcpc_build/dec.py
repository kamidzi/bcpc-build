# Decorators
import os
import sys
from functools import wraps


class ForkFailed(RuntimeError):
    DEFAULT_MSG = 'Fork failed.'

    def __init__(self, message=DEFAULT_MSG):
        super().__init__(message)


def daemonize(close_fds=False):
    """Generates a daemonize decorator

    An example:

        from bcpc_build.dec import daemonize
        import time

        def foo():
            time.sleep(5)
            print('done')

        mutator = daemonize()
        f = mutator(foo)
        f()
    """
    def decorator(f):
        @wraps(f)
        def new_func(*args, **kwargs):
            try:
                pid = os.fork()
                if pid > 0:
                    sys.exit(0)
            except OSError as e:
                raise ForkFailed("first fork failed") from e

            os.setsid()
            try:
                pid = os.fork()
                if pid > 0:
                    sys.exit(0)
                else:
                    if close_fds:
                        with open('/dev/null') as dev_null:
                            open_fds = [int(x)
                                        for x in os.listdir('/proc/self/fd')]
                            for fd in open_fds:
                                d = os.dup(fd)
                                os.dup2(dev_null.fileno(), d)
            except OSError:
                raise ForkFailed("second fork failed") from e
            return f(*args, **kwargs)
        return new_func
    return decorator


if __name__ == '__main__':

    import time
    close_fds = False

    @daemonize(close_fds=close_fds)
    def test():
        open_fds = os.listdir('/proc/self/fd')
        open_fds = open_fds[1:]
        if not open_fds:
            time.sleep(120)
            with open('/tmp/out', 'w') as f:
                f.write('open fds: %s' % open_fds)
        else:
            print('open fds: %s' % open_fds)

    test()
#    print('After the exec.')
