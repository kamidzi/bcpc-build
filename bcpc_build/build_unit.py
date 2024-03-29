from abc import ABC
from abc import abstractmethod
from collections import OrderedDict
from functools import total_ordering
from itertools import chain
from pwd import getpwnam
from subprocess import check_output
from textwrap import dedent
import logging
import os
import shlex
import shutil
import string
import subprocess
import sys

from furl import furl
from psutil import process_iter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import shortuuid

from bcpc_build.db.models.build_unit import BuildStateEnum
from bcpc_build.db.models.build_unit import BuildUnitBase
from bcpc_build.exceptions import *
from bcpc_build import config
from bcpc_build import utils
from bcpc_build.unit import V8ConfigHandler
from bcpc_build.utils.credentials import impersonated_thread

try:
    import simplejson as json
except ImportError:
    import json


@total_ordering
class BuildUnit(BuildUnitBase):
    _jsonattrs_ = (
        'name',
        'source_url',
        'build_user',
        'build_dir',
        'build_state',
    )

    _attrs_ = tuple(['id'] + list(_jsonattrs_))

    @classmethod
    def get_json_dict(cls, bunit):
        d = OrderedDict({'id': str(bunit.id)})
        d.update(OrderedDict(
            map(lambda k: (k, str(getattr(bunit, k))), cls._jsonattrs_))
        )
        # FIXME(kmidzi)
        return d

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def __eq__(self, other):
        get_attrs = self.__class__.get_json_dict
        self_attrs = get_attrs(self)
        other_attrs = get_attrs(other)
        return self_attrs == other_attrs

    def __lt__(self, other):
        def name_key(obj):
            try:
                name = obj.name
                parts = name.split('.')
                key = (int(parts[-1]), name)
            except ValueError:
                key = (sys.maxsize, name)
            except NameError:
                key = (obj,)
            return key

        lval = tuple([*name_key(self), self.build_user])
        rval = tuple([*name_key(other), self.build_user])
        return lval < rval

    def populate(self, allocator, conf={}):
        allocator.populate(self, conf)

    def configure(self, allocator):
        allocator.configure(self)

    def get_build_path(self):
        build_home = BuildUnitAllocator.DEFAULT_BUILD_HOME
        return os.path.join(build_home, self.build_user)

    def to_json(self):
        indent = 2
        info = self.get_json_dict(self)
        return json.dumps(info, indent=indent)


class BuildLogger(object):
    def __init__(self, filename=None, stream=None, func=None, **kwargs):
        self.filename = filename
        self.stream = stream
        self.func = func

        def _prepare_dests():
            self._dests = []
            if stream:
                # TODO(kmidzi): open files?
                self._dests.append(stream)
            if filename:
                # TODO(kmidzi): open files?
                self._dests.append(open(filename, 'w'))
            if not self._dests:
                raise ValueError('No valid destinations supplied.')

        _prepare_dests()

    def echo(self, data):
        return self.write(data, raw=False)

    def write(self, data, raw=True):
        # Never mod input to supplied function
        cooked_data = data if raw else data + '\n'
        for d in self._dests:
            d.write(cooked_data)
        if self.func:
            self.func(data)

    def flush(self):
        for d in self._dests:
            d.flush()

    def __repr__(self):
        attrs = ['filename', 'stream', 'func']
        kwargs = dict(map(lambda a: (a, getattr(self, a)), attrs))
        return ('<BuildLogger (filename={filename}, stream={stream})>'
                ''.format(**kwargs))


class BuildUnitAllocator(ABC):
    BUILD_DIR_PREFIX = 'chef-bcpc.'
    BUILD_STRATEGY_DEFAULT = 'v8'
    BUILD_STRATEGY_NAMES = ['v7', 'v8']
    DEFAULT_BUILD_HOME = '/build'
    DEFAULT_SHELL = '/bin/bash'
    DEFAULT_SRC_URL = 'https://github.com/bloomberg/chef-bcpc'
    SRC_DEPENDS = None

    def __init__(self, *args, **kwargs):
        self._conf = kwargs.get('conf', {})
        self._conf.setdefault('build_home', self.DEFAULT_BUILD_HOME)
        self._logger = logging.getLogger(__name__)
        self._session = kwargs.get('session', None)

    @staticmethod
    def get_allocator(conf, *args, **kwargs):
        class_map = {
            'v7': V7BuildUnitAllocator,
            'v8': V8BuildUnitAllocator,
        }
        strategy = conf['strategy']
        try:
            cls = class_map[strategy]
            return cls(*args, **kwargs)
        except KeyError:
            raise AllocationError('No allocators defined for strategy "{}"'
                                  ''.format(strategy))

    @staticmethod
    def get_build_log(bunit):
        # TODO(kmidzi): simple
        LOGNAME = 'build.log'
        bpath = bunit.get_build_path()
        return os.path.join(bpath, LOGNAME)

    @property
    def session(self):
        if self._session is None:
            engine = create_engine(config.db.url)
            conn = engine.connect()
            Session = sessionmaker(bind=conn)
            self._session = Session()
        return self._session

    @property
    def conf(self):
        return self._conf

    @property
    def logger(self):
        return self._logger

    def setup(self):
        build_home = self.conf.get('build_home')

        def create_build_home():
            mode = 0o2755
            try:
                os.mkdir(path=build_home, mode=mode)
                self.logger.info('Created build home at {}'.format(build_home))
            except PermissionError:
                sys.exit('Setup requires superuser privileges.')

        if not os.path.exists(build_home):
            create_build_home()

    # @abstractmethod
    def build(self, bunit):
        raise NotImplementedError

    def _build_with_command(self, bunit, cmd):
        proc = subprocess.Popen(shlex.split(cmd),
                                stdout=subprocess.PIPE,
                                universal_newlines=True)

        # Need start_new_session to run in background?
        def exit_condition(status):
            if status == 0:
                return True
            elif status < 0:
                raise SignalException(status)
            else:
                raise NonZeroExit(status)

        try:
            while True:
                output = proc.stdout.readline().strip()
                status = proc.poll()
                if output == '' and status is not None:
                    if exit_condition(status):
                        break
                if output:
                    yield output
        except NonZeroExit as e:
            self.set_build_state(bunit, BuildStateEnum.failed_build)
            raise BuildError(e) from e

    def set_build_state(self, bunit, state):
        if not isinstance(state, BuildStateEnum):
            raise ValueError('Incompatible build state.')

        # TODO(kmidzi): re-using same session. Issues?
        bunit.build_state = state
        self.session.add(bunit)
        self.session.commit()

    def install_certs(self, bunit):
        CERTS_DIR = '/var/tmp/bcpc-cacerts'

        basedir = bunit.get_build_path()
        user, group = [bunit.build_user]*2
        # local certificate store in build area
        dest = os.path.join(basedir, 'cacerts')

        def install_copy(src, dst, *d, follow_symlinks=True):
            shutil.copy2(src, dst, *d, follow_symlinks=follow_symlinks)
            # also chown the files
            shutil.chown(dst, user=user, group=group)

        try:
            bunit.logger.info('Installing certificates to %s' % dest)
            shutil.copytree(src=CERTS_DIR, dst=dest, symlinks=True,
                            copy_function=install_copy)
            shutil.chown(dest, user=user, group=group)
        except shutil.Error as e:
            bunit.logger.error('Could not install certificates.')
            sys.exit(e)

    # @abstractmethod
    def configure(self, bunit, *args, **kwargs):
        """Configures the build unit."""
        raise NotImplementedError()

    @classmethod
    def populate(cls, bunit, conf={}, *args, **kwargs):
        src_depends = conf.get('src_depends') or cls.SRC_DEPENDS or {}
        src_url = bunit.source_url
        build_path = bunit.get_build_path()
        logger = bunit.logger
        log_level = conf.get('log_level')
        if log_level is not None:
            utils.set_log_level(logger, log_level)

        # FIXME(kamidzi): git-credential helper?
        def git_args(url):
            url = furl(url)
            path = url.path
            scheme = url.scheme
            # Translate branch url to git arguments
            args = {}
            args['clone'] = '-n -q'
            args['git'] = '-C %s' % build_path
            if scheme in conf:
                proxy = conf[scheme].get('proxy')
                if proxy:
                    args['git'] += ' -c %s.proxy="%s"' % (scheme, proxy)

            if 'credentials' in conf:
                logger.debug(
                    'Detected credentials in configuration: ignoring...'
                )
            args['url'] = url.url
            try:
                path, rev = str(path).split('/tree/')
                logger.debug('Detected branch %s from source url' % rev)
                args['revision'] = rev
                url.set(path=path)
                args['url'] = url.url
            except (ValueError,) as e:
                logger.debug('Revision/branch detection error: %s' % e)
            return args

        def get_cmds(url, name):
            def _checkout_cmd(rev, dest):
                cmd = (
                    "su -c"
                    " 'git -C {dest} fetch -q origin {rev} &&"
                    " git -C {dest} checkout -q FETCH_HEAD' "
                    " {username}"
                ).format(rev=rev, username=bunit.build_user, dest=dest)
                logger.debug('Checkout cmd `{}` from rev={}'.format(cmd, rev))
                yield cmd

            def _clone_cmd(src_url, name=''):
                cmd = (
                    "su -c 'git {git_args} clone {clone_args} {url} {name}' "
                    "{username}"
                ).format(
                    git_args=args.get('git', ''),
                    clone_args=args.get('clone', ''), url=args.get('url'),
                    name=name, username=bunit.build_user
                )
                logger.debug(
                    'Clone cmd `{}` from src_url={}'.format(cmd, src_url))
                yield cmd

            cmds = []
            args = git_args(url)
            cmds += _clone_cmd(url, name)
            rev = args.get('revision')
            if rev:
                dest = os.path.join(build_path, name)
                cmds += _checkout_cmd(rev, dest)
            return chain(cmds)

        def process_deps():
            for name in src_depends:
                url = src_depends[name]
                # Suspect logger...
                logger.debug('Processing dependency: {} => {}'
                             ''.format(name, url))
                for cmd in get_cmds(url, name):
                    check_output(shlex.split(cmd))

        logger.info('Populating build unit...')
        process_deps()
        for cmd in get_cmds(src_url, 'chef-bcpc'):
            check_output(shlex.split(cmd))

    def provision(self, build, *args, **kwargs):
        conf = kwargs.get('conf', {}).copy()
        conf.setdefault('src_depends', self.SRC_DEPENDS)
        try:
            self.logger.info('Provisioning build unit...')
            self.logger.debug({'conf': conf})
            self.set_build_state(build, BuildStateEnum.provisioning)
            self.populate(build, conf=conf)
            # FIXME(kmidzi): sus
            if conf['configure']:
                self.configure(build, src_depends=conf.get('src_depends'))
            self.set_build_state(build, BuildStateEnum.provisioned)
        except Exception as e:
            self.set_build_state(build, BuildStateEnum.failed_provision)
            raise ProvisionError(e) from e
        return build

    def destroy(self, bunit, commit=True):
        # find processes
        # kill processes
        # userdel -r
        def get_procs(user):
            p_attrs = ['pid', 'username']
            plist = list(filter(lambda p: p.info['username'] == user,
                                process_iter(p_attrs)))
            return plist

        def kill_user_procs(user):
            plist = get_procs(user)
            for proc in plist:
                # multiproc here?
                utils.kill_proc_tree(proc.info['pid'])

        def remove_user(user):
            kill_user_procs(user)
            try:
                utils.userdel(user)
            except subprocess.CalledProcessError as e:
                # User does not exist - man(5) userdel
                if e.returncode == 6:
                    self.logger.info("Ignoring non-existent user '%s'" % user)
                else:
                    raise

        remove_user(bunit.build_user)
        if commit:
            self._deallocate(bunit)

    def _deallocate(self, bunit):
        self.session.delete(bunit)
        self.session.commit()

    def allocate(self, *args, **kwargs):
        kwargs = kwargs.copy()
        name = kwargs.pop('name')
        if name:
            bunit = self.session.query(BuildUnit).filter(
                BuildUnit.name == name
            ).one_or_none()
            if bunit:
                raise DuplicateNameError(name)
            # FIXME(kmidzi): complicated by name='' default for optional arg
            kwargs['name'] = name
        build_user = self.allocate_build_user(self.generate_build_user_name())
        kwargs.setdefault('build_user', build_user)
        kwargs.setdefault('name', build_user)
        build_dir = self.allocate_build_dir(**kwargs)
        kwargs.setdefault('build_dir', build_dir)
        bunit = BuildUnit(**kwargs)
        self.session.add(bunit)
        self.session.commit()
        return bunit

    def generate_build_user_name(self):
        id_len = 8
        new_id = shortuuid.uuid()[0:id_len]
        return ''.join([self.BUILD_DIR_PREFIX, str(new_id)])

    def allocate_build_user(self, username):
        # TODO(kmidzi): check for existing files, etc...
        try:
            getpwnam(username)
            self.logger.debug('Build user {} already exits.'.format(username))
        except KeyError:
            self.logger.info('Creating build user {} ...'.format(username))
            try:
                # TODO(kmidzi): allow passing of mode
                utils.useradd(username, shell=self.DEFAULT_SHELL,
                              homedir_prefix=self.conf.get('build_home'))
            except Exception as e:
                print('Could not create user {}. Check euid in calling'
                      ' environment?'.format(username), file=sys.stderr)
                sys.exit(e)
        return username

    def allocate_build_dir(self, *args, **kwargs):
        """Allocates a Build Unit data directory"""
        build_user = kwargs.get('build_user', self.generate_build_user_name())
        # Really, build_user homedir is required...
        try:
            u = getpwnam(build_user)
            path = u.pw_dir
            if not path:
                raise ValueError('pw_dir')
        except (KeyError, ValueError):
            path = os.path.join(self.conf.get('build_home'), build_user)
        return path


class V7BuildUnitAllocator(BuildUnitAllocator):
    DEFAULT_BUILD_STRATEGY = 'v7'
    CONF_TEMPLATE = dedent("""\
        export BCPC_VM_DIR=${build_dir}/bcpc-vms
        export BCPC_HYPERVISOR_DOMAIN=hypervisor-bcpc.example.com
        export BOOTSTRAP_ADDITIONAL_CACERTS_DIR=${build_dir}/cacerts
        export BOOTSTRAP_APT_MIRROR=
        export BOOTSTRAP_CACHE_DIR=${build_dir}/.bcpc-cache
        export BOOTSTRAP_CHEF_DO_CONVERGE=1
        export BOOTSTRAP_CHEF_ENV=Test-Laptop-Vagrant
        export BOOTSTRAP_HTTP_PROXY_URL=${http_proxy_url}
        export BOOTSTRAP_HTTPS_PROXY_URL=${https_proxy_url}
        export BOOTSTRAP_VM_CPUS=2
        export BOOTSTRAP_VM_DRIVE_SIZE=20480
        export BOOTSTRAP_VM_MEM=2048
        export CLUSTER_VM_CPUS=2
        export CLUSTER_VM_DRIVE_SIZE=20480
        export CLUSTER_VM_MEM=3072
        export FILECACHE_MOUNT_POINT=/chef-bcpc-files
        export MONITORING_NODES=0
        export REPO_MOUNT_POINT=/chef-bcpc-host
        export VM_SWAP_SIZE=8192
    """)

    def build(self, bunit):
        self.set_build_state(bunit, BuildStateEnum.building)
        build_user = bunit.build_user
        cmd = ("su -c \"bash -c 'cd chef-bcpc/bootstrap/vagrant_scripts &&"
               " time ./BOOT_GO.sh'\" -"
               " {build_user}".format(build_user=build_user))
        self.logger.debug('Building with command `%s`' % cmd)
        return self._build_with_command(bunit, cmd)

    def configure(self, bunit, *args, **kwargs):
        """Configures the build unit."""
        basedir = bunit.get_build_path()
        workdir = os.path.join(basedir, 'chef-bcpc')
        conf_dir = os.path.join(workdir, 'bootstrap', 'config')
        conffile = os.path.join(conf_dir, 'bootstrap_config.sh.overrides')
        logger = bunit.logger

        tmpl_src = self.CONF_TEMPLATE
        tmpl = string.Template(tmpl_src)
        # TODO(kmidzi): get from somewhere??
        values = {
            'build_dir': basedir,
            'http_proxy_url': 'http://proxy.example.com:3128',
            'https_proxy_url': 'http://proxy.example.com:3128',
        }
        configuration = tmpl.substitute(values)
        self.set_build_state(bunit, BuildStateEnum.configuring)
        with open(conffile, 'w') as c:
            logger.info('Writing build configuration to %s' % conffile)
            logger.debug(
                json.dumps({
                    'Configuration': configuration.split('\n')
                }, indent=2)
            )
            c.write(configuration)
            perms = {'user': bunit.build_user, 'group': bunit.build_user}
            logger.debug('Setting permissions {perms} on configuration'
                         ' file at {filename}'.format(perms=perms,
                                                      filename=conffile))
            shutil.chown(conffile, **perms)

        self.install_certs(bunit)
        self.set_build_state(bunit, BuildStateEnum.configured)


class V8BuildUnitAllocator(BuildUnitAllocator):
    DEFAULT_BUILD_STRATEGY = 'v8'

    def _base_build(self, bunit):
        build_user = bunit.build_user
        cmd = ("su -c \"bash -c 'cd chef-bcpc && time make create all'\""
               " - {build_user}".format(build_user=build_user))
        self.logger.debug('Building with command `%s`' % cmd)
        return self._build_with_command(bunit, cmd)

    def build(self, bunit):
        base = self._base_build(bunit)
        self.set_build_state(bunit, BuildStateEnum.building)
        return base

    def get_build_config(self, bunit):
        bconf = V8ConfigHandler(bunit)
        return bconf

    def configure(self, bunit, *args, **kwargs):
        logger = bunit.logger
        bunit_config = self.get_build_config(bunit)
        self.set_build_state(bunit, BuildStateEnum.configuring)

        # update the networks with generated ids
        comp = 'chef-bcpc'
        config_handler = bunit_config
        nt_component_conf = config_handler.configs[comp]
        networks = list(config_handler.configs[comp].enumerate_nets())

        core_configs = config_handler.configs['chef-bcpc']
        cfg_prefix = 'topology/topology.yml'
        conf = core_configs.configs[cfg_prefix]
        netmap = impersonated_thread(
            bunit.build_user, utils.generate_netids_from_system, args=networks,
            chdir=False
        )

        def update_cluster_networks(conf):
            logger.info('Updating cluster network configuration for %s'
                        '' % bunit_config.bunit.name)
            nodes = conf.get('nodes', {})
            for _node in nodes:
                # only get transit interfaces?
                ifaces = _node['host_vars']['interfaces']['transit']
                for iface in ifaces:
                    net = iface.get('neighbor', {}).get('name')
                    if net:
                        iface['neighbor']['name'] = netmap.get(net, net)
            return conf

        try:
            with conf.edit(backup=True) as contents:
                logger.debug(
                    'Originally loaded data:\n{data}'.format(data=contents))
                update_cluster_networks(contents)
            self.set_build_state(bunit, BuildStateEnum.configured)
        except Exception as e:
            raise ConfigurationError(e) from e


DEFAULT_ALLOCATOR = V8BuildUnitAllocator
