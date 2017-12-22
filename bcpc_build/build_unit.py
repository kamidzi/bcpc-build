#!/usr/bin/env python3
import click
import os
from exceptions import *
from pwd import getpwnam
from subprocess import check_output
from textwrap import dedent
import logging
import os
import shlex
import shutil
import string
import sys
try:
    import simplejson as json
except ImportError:
    import json


class NotImplementedError(Exception):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


class BuildUnit(object):
    def __init__(self, name=None):
        self.build_dir = None
        self.source_url = None
        self.build_user = None
        self.name = name
        self.id = None

        self.logger = logging.getLogger(__name__)

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
        info = {
            'build_dir': self.build_dir or self.get_build_path(),
            'source_url': self.source_url or '',
            'build_user': self.build_user or '',
            'name': self.name or '',
            'id': self.id or '',
        }
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
    def list_build_areas(self):
        # TODO(kmidzi): should this return [] ???
        try:
            return os.listdir(self.conf.get('build_home'))
        except FileNotFoundError as e:
            return []

    def allocate(name=None, *args, **kwargs):
        pass

    def allocate_build_dir(self, *args, **kwargs):
        """Allocates a Build Unit data directory"""
        dirs = self.list_build_areas()

        # get the suffixes
        def split_suffix(x):
            return int(x.split('.')[-1])

        latest = 0 if not dirs else max(map(split_suffix, dirs))
        new_id = latest + 1
        return os.path.join(self.conf.get('build_home'),
                            self.BUILD_DIR_PREFIX + str(new_id))


@click.group()
def cli():
    pass

@cli.command()
@click.option('--source-url', default=BuildUnitAllocator.DEFAULT_SRC_URL, help='Sources for build.')
def build(source_url='ca'):
    BuildUnit('name').configure()
    import subprocess
    import shlex
    import os

    import sys
    current_dir = os.path.normpath(os.path.realpath(os.path.dirname(__file__)))
    bin_path = os.path.join(current_dir, 'init-build-area.py')
    cmd_str  = ('env BUILD_SRC_URL="{source_url}" {bin_path}'
                ''.format(**locals()))
    cmd = shlex.split(cmd_str)
    o = subprocess.check_output(cmd)
    sys.exit(o)


@cli.command()
@click.option('--format', help='Listing format')
def list(format):
    pass

if __name__ == '__main__':
    cli()
