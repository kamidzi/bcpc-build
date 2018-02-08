from bcpc_build.build_unit import BuildUnitAllocator
from bcpc_build.build_unit import NotImplementedError
from bcpc_build.build_unit import BuildUnit
from bcpc_build.db import utils
import click
import os
import shlex
import subprocess
import sys
try:
    import simplejson as json
except ImportError:
    import json


class BuildUnitListingJSONFormat(object):
    @staticmethod
    def format(data):
        return json.dumps(data, indent=2)


@click.group(help='Manages build units.')
@click.pass_context
def cli(ctx):
    pass


@cli.command(help='Initiate a build of a unit.')
@click.pass_context
def build(ctx, source_url):
    allocator = BuildUnitAllocator()
    allocator.setup()
    build = allocator.allocate()
    allocator.provision(build)
    click.echo(build.to_json())


@cli.command(help='List build units')
@click.pass_context
@click.option('--format', help='Listing format', default='json')
def list(ctx, format):
    formatters = {
        'json': BuildUnitListingJSONFormat
    }

    session = utils.Session()
    builds = session.query(BuildUnit)
    try:
        formatter = formatters[format]
    except KeyError:
        raise NotImplementedError('%s format' % format)

    click.echo(formatter.format(sorted(builds)))
