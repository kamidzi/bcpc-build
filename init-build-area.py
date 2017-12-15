#!/usr/bin/env python3
import os
import logging
import sys
import shlex
from shutil import chown
from pwd import getpwnam
from subprocess import check_output
from bcpc_build import utils

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BUILD_HOME = '/build'
# Also the username
BUILD_DIR_PREFIX = 'chef-bcpc.'


class AllocationError(Exception):
    _MESSAGE = 'Error allocating build area. Existing areas: %s'
    # TODO(kmidzi): careful about length of _areas_

    def __init__(self, areas):
        message = self._MESSAGE % areas
        super(AllocationError, self).__init__(message)


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

        def populate_build_unit():
            logger.info('Populating build unit...')
            src_url = 'https://github.com/bloomberg/chef-bcpc'
            cmd = ("su -c 'git -C {dest} clone {url}' "
                   "{username}").format(dest=build_path,
                                        url=src_url,
                                        username=name)
            check_output(shlex.split(cmd))

        # TODO(kmidzi): check for existing files, etc...
        try:
            getpwnam(name)
            logger.debug('Build user {} already exits.'.format(name))
        except KeyError:
            logger.info('Creating build user {} ...'.format(name))
            try:
                utils.useradd(name)
            except Exception as e:
                print('Could not create user {}. Check euid in calling'
                      ' environment?'.format(name), file=sys.stderr)
                sys.exit(e)

        build_path = get_build_path(name)
        # create the directory
        os.mkdir(build_path)
        chown(build_path, name)
        # populate
        populate_build_unit()

    initialize_build_unit(username)
