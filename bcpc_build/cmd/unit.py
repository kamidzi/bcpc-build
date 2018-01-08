from bcpc_build.build_unit import BuildUnitAllocator
import click
import os
import shlex
import subprocess
import sys

@click.group()
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
@click.option('--format', help='Listing format')
def list(ctx, format):
    # Quick and dirty
    try:
        import simplejson as json
    except ImportError:
        import json
        
    builds = os.listdir(BuildUnitAllocator.DEFAULT_BUILD_HOME)
    click.echo(json.dumps(sorted(builds), indent=2))
