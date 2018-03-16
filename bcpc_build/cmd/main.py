from bcpc_build.build_unit import BuildUnitAllocator
import click
import logging
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


### add some subcommands ###
from bcpc_build.cmd.bootstrap import bootstrap
from bcpc_build.cmd.db import cli as db_cmds
from bcpc_build.cmd.setup import init
from bcpc_build.cmd.setup import setup
from bcpc_build.cmd.unit import cli as unit_cmds

cli.add_command(init)
cli.add_command(bootstrap)
cli.add_command(unit_cmds, name='unit')
cli.add_command(db_cmds, name='db')

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
