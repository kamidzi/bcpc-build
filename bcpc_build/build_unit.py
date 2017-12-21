#!/usr/bin/env python3
import click

DEFAULT_SRC_URL = 'https://github.com/bloomberg/chef-bcpc'

@click.group()
def cli():
    pass

@cli.command()
@click.option('--source-url', default=DEFAULT_SRC_URL, help='Sources for build.')
def build(source_url='ca'):
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
