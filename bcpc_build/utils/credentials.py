from pwd import getpwnam
from warnings import warn
import contextlib
import multiprocessing
import os
import sys

from bcpc_build.unit import ConfigFile
import furl
import click


@contextlib.contextmanager
def nullcontext():
    try:
        yield
    finally:
        pass


class NoSuchActionError(RuntimeError):
    pass


class GitCredentialHelper:
    def __init__(self, conf, **kwargs):
        self.conf = conf

    @staticmethod
    def parse_input(stream=sys.stdin):
        DELIM = '='

        def _yield_kvs(data):
            for assign in lines:
                k, v = assign.strip().split(DELIM)
                yield (k, v)

        try:
            lines = stream.readlines()
            return dict(_yield_kvs(lines))
        except Exception as e:
            sys.exit(e)

    def get(self):
        def _format_kvs(data):
            return '\n'.join(map(lambda k: '{}={}'.format(k, data[k]), data))

        def _mk_origin(**kwargs):
            url = furl.furl()
            for k in kwargs:
                setattr(url, k, kwargs[k])
            return url.origin

        inputs = self.parse_input()
        conf_key = _mk_origin(scheme=inputs['protocol'], **inputs)
        ans = _format_kvs(self.conf.contents[conf_key])
        return ans

    def store(self):
        raise NotImplementedError

    def erase(self):
        raise NotImplementedError

    def run_action(self, action, *args):
        try:
            meth = getattr(self, action)
            res = meth(*args)
            if res is not None:
                print(res)
        except AttributeError as e:
            raise NoSuchActionError(action) from e

    @staticmethod
    @click.command(help='Main interface to credential helper.')
    @click.option('--config-file', '-c', type=click.File('r'), required=True)
    @click.argument('command', type=click.Choice('get store erase'.split(' ')),
                    required=True)
    def main(config_file, command):
        # TODO(kmidzi): double file open, etc...
        conf = ConfigFile(config_file.name, config_file.name)
        helper = GitCredentialHelper(conf)
        try:
            helper.run_action(command)
        except NotImplementedError:
            warn('Unimplemented action {} has been requested.'.format(command))
        except Exception as e:
            sys.exit(e)


_AVAILABLE_CONTEXTS = ('euid', 'gid', 'egid')


class UserContextSwitchError(RuntimeError):
    pass


class UserImpersonationError(RuntimeError):
    pass


# https://gist.githubusercontent.com/zeroslack/791496592badc91331c75ac4bf09bfbe/raw/f3c098274bf6167130e3ad0549c69eade492704b/impersonate.py
def _mk_context_switcher(context):
    if context not in _AVAILABLE_CONTEXTS:
        raise ValueError(context)
    _getter, _setter = 'get{}'.format(context), 'set{}'.format(context)
    getter, setter = getattr(os, _getter), getattr(os, _setter)
    _name = 'switch_{}'.format(context)

    @contextlib.contextmanager
    def _switch_context(target):
        original = getter()
        try:
            setter(target)
            yield
        except Exception as e:
            raise UserContextSwitchError() from e
        finally:
            setter(original)

    _switch_context.__name__ = _name
    return _switch_context


for c in _AVAILABLE_CONTEXTS:
    name = 'switch_{}'.format(c)
    globals()[name] = _mk_context_switcher(c)


@contextlib.contextmanager
def env(mapping):
    oldenv = os.environ.copy()
    try:
        os.environ.update(mapping)
        yield
    finally:
        os.environ.clear()
        os.environ.update(oldenv)


@contextlib.contextmanager
def chdir(dest):
    curdir = os.curdir
    try:
        os.chdir(dest)
    finally:
        # TODO(kamidzi): possible with impersonation, this could fail
        os.chdir(curdir)


def impersonated_process(
    username, target, args=(), daemon=False,
    setegid=True, setgid=False, chdir=True, set_home=True
):
    try:
        getpwnam(username)
    except KeyError as e:
        raise UserImpersonationError from e

    if daemon is True:
        raise NotImplementedError('Daemonized threads.')

    if not callable(target):
        raise UserImpersonationError(
            'target is not callable.'
        )

    que_ = multiprocessing.JoinableQueue()

    def impersonate(*args):
        try:
            pw_ent = getpwnam(username)
            if setgid:
                orig_egid = os.getegid()
                os.setgid(pw_ent.pw_gid)
                if not setegid:
                    os.setegid(orig_egid)
            elif setegid and not setgid:
                os.setegid(pw_ent.pw_gid)

            os.setuid(pw_ent.pw_uid)
            if chdir:
                os.chdir(pw_ent.pw_dir)

            if set_home:
                cm = env({'HOME': pw_ent.pw_dir})
            else:
                cm = nullcontext()
            with cm:
                # will need to wrap target in cm
                ret = target.__call__(*args)
            que_.put(ret)
            return ret
        except (KeyError):
            que_.put(
                UserImpersonationError(
                    'Could not find user `{}`'.format(username)
                )
            )
        except Exception as e:
            que_.put(UserImpersonationError(e))

    def is_parent():
        return os.getpid() == os.getppid()

    p = multiprocessing.Process(target=impersonate, args=args, daemon=daemon)
    p.start()
    ret = que_.get()
    if isinstance(ret, Exception):
        raise ret
    que_.task_done()
    return ret
