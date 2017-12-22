#!/usr/bin/env python3
from exceptions import *
from pwd import getpwnam
from subprocess import check_output
from textwrap import dedent
from build_unit import BuildUnit
from build_unit import BuildUnitAllocator
import logging
import os
import shlex
import shutil
import string
import sys
import urllib.parse
import utils
try:
    import simplejson as json
except ImportError:
    import json


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# temp
ALLOCATOR = BuildUnitAllocator()
BUILD_HOME = ALLOCATOR.conf.get('build_home')
# Also the username
BUILD_DIR_PREFIX = ALLOCATOR.BUILD_DIR_PREFIX
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
    return ALLOCATOR.list_build_areas()

def allocate_build_dir(*args, **kwargs):
    return ALLOCATOR.allocate_build_dir(*args, **kwargs)

if __name__ == '__main__':
    setup()
    build_path = allocate_build_dir()
    username = os.path.basename(build_path)
    # Offload to user creation script?

    def initialize_build_unit(name):
        bunit = BuildUnit(name)

        def configure_build_unit(name):
            bunit.configure()

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
        return bunit

    def display_build_info(build):
        print(build.to_json())

    build = initialize_build_unit(username)
    display_build_info(build)
