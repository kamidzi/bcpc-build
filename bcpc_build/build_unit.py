from abc import ABC
from bcpc_build.db.models.build_unit import BuildUnitBase
from bcpc_build.exceptions import *
from bcpc_build import config
from bcpc_build import utils
from collections import OrderedDict
from functools import total_ordering
from pwd import getpwnam
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from subprocess import check_output
from textwrap import dedent
from psutil import process_iter
from furl import furl
import logging
import os
import shortuuid
import shlex
import shutil
import string
import sys
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
    )

    _attrs_ = tuple(['id'] + list(_jsonattrs_))

    @classmethod
    def get_json_dict(cls, bunit):
        d = OrderedDict({'id': str(bunit.id)})
        d.update(OrderedDict(
            map(lambda k: (k, getattr(bunit, k)), cls._jsonattrs_))
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
        return os.path.join(build_home, self.name)

    def to_json(self):
        indent = 2
        info = self.get_json_dict(self)
        return json.dumps(info, indent=2)


class AllocationError(RuntimeError):
    pass


logging.basicConfig(level=logging.INFO, stream=sys.stdout)


class BuildUnitAllocator(ABC):
    BUILD_DIR_PREFIX = 'chef-bcpc.'
    DEFAULT_BUILD_HOME = '/build'
    DEFAULT_SHELL = '/bin/bash'
    BUILD_STRATEGY_NAMES = ['v7', 'v8']
    BUILD_STRATEGY_DEFAULT = 'v7'
    SRC_DEPENDS = None

    def __init__(self, *args, **kwargs):
        self._conf = kwargs.get('conf', {})
        self._conf.setdefault('build_home', self.DEFAULT_BUILD_HOME)
        self._logger = logging.getLogger(__name__)
        self._session = None

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

    # TODO(kamidzi): move me
    def _list_build_areas(self):
        # TODO(kmidzi): should this return [] ???
        try:
            return os.listdir(self.conf.get('build_home'))
        except FileNotFoundError as e:
            return []

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
        with open(conffile, 'w') as c:
            logger.info('Writing build configuration to %s' % conffile)
            logger.debug({'configuration': configuration})
            c.write(configuration)
            perms = {'user': bunit.name, 'group': bunit.name}
            logger.debug('Setting permissions {perms} on configuration'
                         ' file at {filename}'.format(perms=perms,
                                                      filename=conffile))
            shutil.chown(conffile, **perms)

        self.install_certs(bunit)

    @classmethod
    def populate(cls, bunit, conf={}, *args, **kwargs):
        src_depends = cls.SRC_DEPENDS or {}
        src_url = bunit.source_url
        build_path = bunit.get_build_path()
        logger = bunit.logger

        # FIXME(kamidzi): git-credential helper?
        def git_args(url):
            url = furl(url)
            path = url.path
            scheme = url.scheme
            # Translate branch url to git arguments
            args = {}
            args['git'] = '-C %s' % build_path
            if scheme in conf:
                proxy = conf[scheme].get('proxy')
                if proxy:
                    args['git'] += ' -c %s.proxy="%s"' % (scheme, proxy)

            if 'credentials' in conf:
                logger.debug('Detected credentials in configuration')
                creds = conf['credentials']
                url.set(username=creds['username'],
                        password=creds['password'])
            args['url'] = url.url
            try:
                path, branch = str(path).split('/tree/')
                logger.debug('Detected branch %s from source url' % branch)
                args['clone'] = '-b %s' % branch
                # replace the path to exclude branch
                url.set(path=path)
                args['url'] = url.url
            except (ValueError,) as e:
                logger.debug(e)
            return args

        def clone_cmd(src_url, dest=''):
            args = git_args(src_url)
            cmd = ("su -c 'git {git_args} clone {clone_args} {url} {dest}' "
                   "{username}").format(git_args=args.get('git', ''),
                                        clone_args=args.get('clone', ''),
                                        url=args.get('url'),
                                        dest=dest,
                                        username=bunit.build_user)
            logger.debug('Generated `{}` from src_url={}'.format(cmd, src_url))
            return cmd

        def process_deps():
            for name in src_depends:
                url = src_depends[name]
                # Suspect logger...
                logger.debug('Processing dependency: {} => {}'
                             ''.format(name, url))
                cmd = clone_cmd(url, name)
                check_output(shlex.split(cmd))

        process_deps()
        cmd = clone_cmd(src_url, 'chef-bcpc')
        check_output(shlex.split(cmd))

    def provision(self, build, *args, **kwargs):
        conf = kwargs.get('conf', {}).copy()
        self.populate(build, conf=conf)
        self.configure(build)
        return build

    def destroy(self, bunit):
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
            timeout = 3
            for proc in plist:
                # multiproc here?
                kill_proc_tree(proc.info['pid'])

        def remove_user(user):
            kill_user_procs(user)
            utils.userdel(user)

        remove_user(bunit.build_user)
        self._deallocate(bunit)

    def _deallocate(self, bunit):
        self.session.delete(bunit)
        self.session.commit()

    def allocate(self, *args, **kwargs):
        kwargs = kwargs.copy()
        build_user = self.allocate_build_user(self.generate_build_user_name())
        build_dir = self.allocate_build_dir(build_user=build_user)
        kwargs.setdefault('build_user', build_user)
        kwargs.setdefault('build_dir', build_dir)
        kwargs.setdefault('name', build_user)
        bunit = BuildUnit(**kwargs)
        # flush it here
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
        return os.path.join(self.conf.get('build_home'), build_user)


class V7BuildUnitAllocator(BuildUnitAllocator):
    DEFAULT_SRC_URL = 'https://github.com/bloomberg/chef-bcpc'
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



class V8BuildUnitAllocator(BuildUnitAllocator):
    DEFAULT_SRC_URL =\
        'https://github.com/bloomberg/BCPC/chef-bcpc/tree/v8/xenial'
    CONF_TEMPLATE = dedent("""\
        export BCPC_HYPERVISOR_DOMAIN=hypervisor-bcpc.example.com
        export BCPC_VM_DIR=${build_dir}/bcpc-vms
        export BOOTSTRAP_ADDITIONAL_CACERTS_DIR=${build_dir}/cacerts
        export BOOTSTRAP_APT_MIRROR=
        export BOOTSTRAP_CACHE_DIR=${build_dir}/.bcpc-cache
        export BOOTSTRAP_CHEF_DO_CONVERGE=1
        export BOOTSTRAP_CHEF_ENV=Test-Laptop-Vagrant-Multirack
        export BOOTSTRAP_DNS_RESOLVER=10.10.10.10
        export BOOTSTRAP_DOMAIN=bcpc.example.com
        export BOOTSTRAP_HTTP_PROXY_URL=${http_proxy_url}
        export BOOTSTRAP_HTTPS_PROXY_URL=${https_proxy_url}
        export BOOTSTRAP_VM_CPUS=2
        export BOOTSTRAP_VM_DRIVE_SIZE=20480
        export BOOTSTRAP_VM_MEM=4096
        export CLUSTER=multirack
        export CLUSTER_VM_CPUS=2
        export CLUSTER_VM_DRIVE_SIZE=20480
        export CLUSTER_VM_MEM=3072
        export CLUSTER_VM_MEM=8192
        export FILECACHE_MOUNT_POINT=/chef-bcpc-files
        export MONITORING_NODES=0
        export MONITORING_NODES=3
        export REPO_MOUNT_POINT=/chef-bcpc-host
        export REPO_MOUNT_POINT=/chef-bcpc-host
        export VM_SWAP_SIZE=8192
    """)
    SRC_DEPENDS = {
        'leafy-spines': 'https://repo.example.com/private/leafy-spines'
    }


DEFAULT_ALLOCATOR = V7BuildUnitAllocator
