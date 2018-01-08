from bcpc_build.build_unit import BuildUnitAllocator
import click
import shlex
import subprocess
import sys
try:
    import simplejson as json
except ImportError:
    import json


@click.group()
@click.pass_context
def cli(ctx):
    setattr(ctx, 'conf', {})

@cli.group()
@click.pass_context
def unit(ctx):
    """bcpc-build-unit commands"""

@unit.command(help='List build units')
@click.pass_context
def list(ctx):
    pass

### add some subcommands ###

from bcpc_build.cmd.bootstrap import bootstrap
cli.add_command(bootstrap)
