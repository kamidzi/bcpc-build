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

    cmd_str  = ('env BUILD_SRC_URL="{source_url}" init-build-area.py'
                ''.format(**locals()))
    cmd = shlex.split(cmd_str)
    print(__file__)
    print(dir())
    o = subprocess.check_output(cmd)


@cli.command()
@click.option('--format', help='Listing format')
def list(format):
    pass

if __name__ == '__main__':
    cli()
