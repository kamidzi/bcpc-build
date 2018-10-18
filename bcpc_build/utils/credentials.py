from pwd import getpwnam
from warnings import warn
import contextlib
import os
import sys

from bcpc_build.unit import ConfigFile
import furl
import click


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
def impersonate(username, setegid=True, setgid=False, chdir=True):
    try:
        pw_ent = getpwnam(username)
    except KeyError as e:
        raise UserImpersonationError from e
    dir_changed = False
    try:
        cwd = os.curdir
        with contextlib.ExitStack() as stack:
            if setgid:
                orig_egid = os.getegid()
                stack.enter_context(switch_gid(pw_ent.pw_gid))
                if not setegid:
                    stack.enter_context(switch_egid(orig_egid))
            elif setegid and not setgid:
                stack.enter_context(switch_egid(pw_ent.pw_gid))

            if chdir:
                os.chdir(pw_ent.pw_dir)
                dir_changed = True
            stack.enter_context(switch_euid(pw_ent.pw_uid))
            yield
    finally:
        if dir_changed:
            os.chdir(cwd)
