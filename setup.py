from setuptools import setup, find_packages
from distutils.errors import DistutilsSetupError

# from setuptools.config import read_configuration
# process setup.cfg - for uses like `pip install .`
# Assumes python3
import contextlib
import pip
import shlex
import subprocess
import sys
import warnings

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


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

    return list(_process_kvs())


def _mk_pip_fn(command):
    def fn(name, global_opts={}, *args, **kwargs):
        cmd = '{g_opts} {command} {args} {name}'.format(
            g_opts=' '.join(_mk_opts(**global_opts)),
            command=command,
            args=' '.join(_mk_opts(**kwargs)),
            name=name,
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


setup_args = {}
try:
    config = configparser.ConfigParser()
    config.read('setup.cfg')
    # Need setuptools >=30.3.0 ?
    # config = read_configuration('setup.cfg')
    setup_args = dict(config['metadata'])
except Exception as e:
    setup_args = {}
    print('Error reading setup.cfg: %s' % e, file=sys.stderr)

# Update everything from setup.cfg
setup_args.update(
    dict(
        packages=find_packages(),
        # TODO(kmidzi): offload
        entry_points='''
        [console_scripts]
        bcpc-build=bcpc_build.cmd.main:cli
        bcpc-build-db=bcpc_build.cmd.db:cli
        bcpc-build-unit=bcpc_build.cmd.unit:cli
        bcpc-build-unit-config=bcpc_build.cmd.unit.config:cli
    ''',
        use_scm_version=True,
    )
)


def format_setup_args(conf):
    try:
        conf = conf.copy()
        section = conf['classifiers']
        new_vals = list(filter(None, section.split('\n')))
        conf['classifiers'] = new_vals
    except KeyError:
        pass
    return conf


setup_args = format_setup_args(setup_args)
setup(**setup_args)

with buildtime_deps(*BUILD_TIME_DEPS):
    import _setuplib

    try:
        with _setuplib.SDKDownloader().run() as filename:
            _setuplib.VBoxAPIInstaller.run(filename)
            _setuplib.VBoxAPIInstaller.installation_test()
    except _setuplib.requests.exceptions.SSLError as e:
        raise DistutilsSetupError(
            'Try exporting SSL_CERT_DIR if you need additional CA certs.'
        ) from e
