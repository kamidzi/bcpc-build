#!/usr/bin/env python3
import click

DEFAULT_SRC_URL = 'https://github.com/bloomberg/chef-bcpc'

class NotImplementedError(Exception):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


class BuildUnit(object):
    def __init__(self):
        self.build_dir = None
        self.source_url = None
        self.build_user = None
        self.name = None
        self.id = None

    def configure(self):
        """Configures the build unit."""
        raise NotImplementedError()


@click.group()
def cli():
    pass

@cli.command()
@click.option('--source-url', default=DEFAULT_SRC_URL, help='Sources for build.')
def build(source_url='ca'):
    BuildUnit().configure()
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
