import contextlib
import pip
import subprocess
import shlex
import warnings


BUILD_TIME_DEPS = ('lxml', 'requests')


# https://gist.github.com/zeroslack/daa9d85791079417d9217c330fdde146
def _mk_opts(**kwargs):
    def _opt_name(x):
        return x.replace('_', '-')

    def _process_kvs():
        for k in kwargs:
            optname = _opt_name(k)
            flag_spec = '-' if len(optname) == 1 else '--'
            if kwargs[k] is True:
                yield '{}{}'.format(flag_spec, optname)
            else:
                yield '{}{} {}'.format(flag_spec, optname, kwargs[k])

    return(list(_process_kvs()))


def _mk_pip_fn(command):
    def fn(name, global_opts={}, *args, **kwargs):
        cmd = '{g_opts} {command} {args} {name}'.format(
            g_opts=' '.join(_mk_opts(**global_opts)), 
            command=command,
            args=' '.join(_mk_opts(**kwargs)),
            name=name
        )
        return pip.main((shlex.split(cmd)))

    fn.__name__ = 'pip_{}'.format(command)
    return fn


pip_uninstall = _mk_pip_fn('uninstall')
pip_install = _mk_pip_fn('install')


@contextlib.contextmanager
def buildtime_deps(*deps):
    try:
        for d in deps:
            pip_install(d)
        yield
    finally:
        for d in deps:
            try:
                pip_uninstall(d, yes=True)
            except Exception:
                warnings.warn('Failed to uninstall {}'.format(d))


if __name__ == '__main__':
    with buildtime_deps(*BUILD_TIME_DEPS):
        import _setuplib
        _setuplib.VBoxAPIInstaller.installation_test()
#        with _setuplib.SDKDownloader().run(keep_files=True) as filename:
#            _setuplib.VBoxAPIInstaller.run(filename)
#            _setuplib.VBoxAPIInstaller.installation_test()
#
#        with _setuplib.SDKDownloader.cacert_path() as path:
#            import requests
#            requests.get('https://download.virtualbox.org', verify=path)
