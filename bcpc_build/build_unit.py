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
import logging
import os
import shortuuid
import shlex
import shutil
import string
import sys
import urllib.parse
try:
    import simplejson as json
except ImportError:
    import json


class NotImplementedError(Exception):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


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

    def populate(self):
        self.logger.info('Populating build unit...')
        src_url = self.source_url
        build_path = self.get_build_path()

        def git_args(url):
            parsed = urllib.parse.urlparse(url)
            path = urllib.parse.unquote(parsed.path)
            # Translate branch url to git arguments
            args = {}
            args['git'] = '-C %s' % build_path
            args['url'] = url
            try:
                path, branch = path.split('/tree/')
                self.logger.debug('Detected branch %s from source url' % branch)
                args['clone'] = '-b %s' % branch
                # replace the path to exclude branch
                u = parsed._replace(path=path)
                clean_url = urllib.parse.urlunparse(u)
                args['url'] = clean_url
            except (AttributeError, ValueError) as e:
                self.logger.debug(e)
            return args

        args = git_args(src_url)
        cmd = ("su -c 'git {git_args} clone {clone_args} {url}' "
                "{username}").format(git_args=args.get('git', ''),
                                    clone_args=args.get('clone', ''),
                                    url=args.get('url'),
                                    username=self.build_user)
        check_output(shlex.split(cmd))

    def configure(self):
        """Configures the build unit."""
        basedir = self.get_build_path()
        workdir = os.path.join(basedir, 'chef-bcpc')
        conf_dir = os.path.join(workdir, 'bootstrap', 'config')
        conffile = os.path.join(conf_dir, 'bootstrap_config.sh.overrides')

        tmpl_src = dedent("""\
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
        tmpl = string.Template(tmpl_src)
        # TODO(kmidzi): get from somewhere??
        values = {
            'build_dir': basedir,
            'http_proxy_url': 'http://proxy.example.com:3128',
            'https_proxy_url': 'http://proxy.example.com:3128',
        }
        configuration = tmpl.substitute(values)
        with open(conffile, 'w') as c:
            self.logger.info('Writing build configuration to %s' % conffile)
            self.logger.debug({'configuration': configuration})
            c.write(configuration)
            perms = {'user': self.name, 'group': self.name}
            self.logger.debug('Setting permissions {perms} on configuration'
                            ' file at {filename}'.format(perms=perms,
                                                        filename=conffile))
            shutil.chown(conffile, **perms)

        def install_certs():
            CERTS_DIR = '/var/tmp/bcpc-cacerts'

            user, group = [self.name]*2
            # local certificate store in build area
            dest = os.path.join(basedir, 'cacerts')

            def install_copy(src, dst, *d, follow_symlinks=True):
                shutil.copy2(src, dst, *d, follow_symlinks=follow_symlinks)
                # also chown the files
                shutil.chown(dst, user=user, group=group)

            try:
                self.logger.info('Installing certificates to %s' % dest)
                shutil.copytree(src=CERTS_DIR, dst=dest, symlinks=True,
                                copy_function=install_copy)
                shutil.chown(dest, user=user, group=group)
            except shutil.Error as e:
                self.logger.error('Could not install certificates.')
                sys.exit(e)

        install_certs()

    def get_build_path(self):
        build_home = BuildUnitAllocator.DEFAULT_BUILD_HOME
        return os.path.join(build_home, self.name)

    def to_json(self):
        indent = 2
        info = self.get_json_dict(self)
        return json.dumps(info, indent=2)


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
class BuildUnitAllocator(object):
    DEFAULT_SRC_URL = 'https://github.com/bloomberg/chef-bcpc'
    BUILD_DIR_PREFIX = 'chef-bcpc.'
    DEFAULT_BUILD_HOME = '/build'

    def __init__(self, *args, **kwargs):
        self._conf = kwargs.get('conf', {})
        self._conf.setdefault('build_home', self.DEFAULT_BUILD_HOME)
        self._conf.setdefault('src_url', self.DEFAULT_SRC_URL)
        self._logger = logging.getLogger(__name__)
        self._session = None

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

    def provision(self, build, *args, **kwargs):
        build.populate()
        build.configure()
        return build

    def allocate(self, *args, **kwargs):
        kwargs = kwargs.copy()
        build_user = self.allocate_build_user(self.generate_build_user_name())
        build_dir = self.allocate_build_dir(build_user=build_user)
        kwargs.setdefault('source_url', self.DEFAULT_SRC_URL)
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
                utils.useradd(username, homedir_prefix=self.conf.get('build_home'))
            except Exception as e:
                print('Could not create user {}. Check euid in calling'
                      ' environment?'.format(username), file=sys.stderr)
                sys.exit(e)
        return username

    def allocate_build_dir(self, *args, **kwargs):
        """Allocates a Build Unit data directory"""
        build_user = kwargs.get('build_user', self.generate_build_user_name())
        return os.path.join(self.conf.get('build_home'), build_user)
