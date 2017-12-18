#!/usr/bin/env python3
from bcpc_build import utils
from pwd import getpwnam
from subprocess import check_output
from textwrap import dedent
from bcpc_build.exceptions import *
import logging
import os
import shlex
import shutil
import string
import sys
import urllib.parse
try:
    import simplejson as json
except ImportError:
    import json


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BUILD_HOME = '/build'
# Also the username
BUILD_DIR_PREFIX = 'chef-bcpc.'
BUILD_SRC_URL = os.environ.get('BUILD_SRC_URL',
                               'https://github.com/bloomberg/chef-bcpc')


def setup(conf=None):

    def create_build_home():
        mode = 0o2755
        try:
            os.mkdir(path=BUILD_HOME, mode=mode)
            logger.info('Created build home at {}'.format(BUILD_HOME))
        except PermissionError:
            sys.exit('Setup requires superuser privileges.')

    if not os.path.exists(BUILD_HOME):
        create_build_home()


def list_build_areas():
    # TODO(kmidzi): should this return [] ???
    try:
        return os.listdir(BUILD_HOME)
    except FileNotFoundError as e:
        return []


def allocate_build_dir(*args, **kwargs):
    dirs = list_build_areas()

    # get the suffixes
    def split_suffix(x):
        return int(x.split('.')[-1])

    latest = 0 if not dirs else max(map(split_suffix, dirs))
    new_id = latest + 1
    return os.path.join(BUILD_HOME, BUILD_DIR_PREFIX + str(new_id))


if __name__ == '__main__':
    setup()
    build_path = allocate_build_dir()
    username = os.path.basename(build_path)
    # Offload to user creation script?

    def initialize_build_unit(name):

        def get_build_path(name):
            return os.path.join(BUILD_HOME, name)

        def configure_build_unit(name):
            basedir = get_build_path(name)
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
                logger.info('Writing build configuration to %s' % conffile)
                logger.debug({'configuration': configuration})
                c.write(configuration)
                perms = {'user': name, 'group': name}
                logger.debug('Setting permissions {perms} on configuration'
                             ' file at {filename}'.format(perms=perms,
                                                          filename=conffile))
                shutil.chown(conffile, **perms)

            def install_certs():
                CERTS_DIR = '/var/tmp/bcpc-cacerts'

                user, group = [name]*2
                # local certificate store in build area
                dest = os.path.join(basedir, 'cacerts')

                def install_copy(src, dst, *d, follow_symlinks=True):
                    shutil.copy2(src, dst, *d, follow_symlinks=follow_symlinks)
                    # also chown the files
                    shutil.chown(dst, user=user, group=group)

                try:
                    logger.info('Installing certificates to %s' % dest)
                    shutil.copytree(src=CERTS_DIR, dst=dest, symlinks=True,
                                    copy_function=install_copy)
                    shutil.chown(dest, user=user, group=group)
                except shutil.Error as e:
                    logger.error('Could not install certificates.')
                    sys.exit(e)

            install_certs()

        def populate_build_unit(name):
            logger.info('Populating build unit...')
            src_url = BUILD_SRC_URL

            def git_args(url):
                parsed = urllib.parse.urlparse(url)
                path = urllib.parse.unquote(parsed.path)
                # Translate branch url to git arguments
                args = {}
                args['git'] = '-C %s' % build_path
                args['url'] = url
                try:
                    path, branch = path.split('/tree/')
                    logger.debug('Detected branch %s from source url' % branch)
                    args['clone'] = '-b %s' % branch
                    # replace the path to exclude branch
                    u = parsed._replace(path=path)
                    clean_url = urllib.parse.urlunparse(u)
                    args['url'] = clean_url
                except (AttributeError, ValueError) as e:
                    logger.debug(e)
                return args

            args = git_args(src_url)
            cmd = ("su -c 'git {git_args} clone {clone_args} {url}' "
                   "{username}").format(git_args=args.get('git', ''),
                                        clone_args=args.get('clone', ''),
                                        url=args.get('url'),
                                        username=name)
            check_output(shlex.split(cmd))

        # TODO(kmidzi): check for existing files, etc...
        try:
            getpwnam(name)
            logger.debug('Build user {} already exits.'.format(name))
        except KeyError:
            logger.info('Creating build user {} ...'.format(name))
            try:
                # TODO(kmidzi): allow passing of mode
                utils.useradd(name, homedir_prefix=BUILD_HOME)
            except Exception as e:
                print('Could not create user {}. Check euid in calling'
                      ' environment?'.format(name), file=sys.stderr)
                sys.exit(e)

        # populate
        populate_build_unit(name)
        configure_build_unit(name)

    def display_build_info(build_id=None):
        info = {
            'build_dir': build_path,
            'source_url': BUILD_SRC_URL,
            'build_user': username,
        }
        print(json.dumps(info, indent=2))

    initialize_build_unit(username)
    display_build_info()
