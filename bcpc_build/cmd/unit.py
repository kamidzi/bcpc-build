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
from json import JSONEncoder

class BuildUnitListingJSONFormat(object):
    class BuildUnitEncoder(object):
        @staticmethod
        def default(obj):
            if isinstance(obj, BuildUnit):
                return BuildUnit.get_json_dict(obj)
            else:
                return obj

    @staticmethod
    def format(data):
        BuildUnitEncoder = BuildUnitListingJSONFormat.BuildUnitEncoder
        return json.dumps(data, default=BuildUnitEncoder.default, indent=2)


@click.group(help='Manages build units.')
@click.pass_context
def cli(ctx):
    pass


@cli.command(help='Initiate a build of a unit.')
@click.pass_context
@click.option('--source-url', help='Source url for the build.', required=True)
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
    import builtins
    formatters = {
        'json': BuildUnitListingJSONFormat
    }

    session = utils.Session()
    builds = session.query(BuildUnit)
    if not builtins.list(builds):
        return
    try:
        formatter = formatters[format]
    except KeyError:
        raise NotImplementedError('%s format' % format)

    click.echo(formatter.format(sorted(builds)))
