from bcpc_build.build_unit import BuildUnitAllocator
import click
import os
import shlex
import subprocess
import sys

@click.group()
@click.pass_context
def cli(ctx):
    ctx.conf = {}

@cli.command()
@click.option('--source-url', default=BuildUnitAllocator.DEFAULT_SRC_URL,
              help='URL for build sources.')
def bootstrap(source_url):
    ctx.conf['src_url'] = source_url
    allocator = BuildUnitAllocator(conf=ctx.conf.copy())
    allocator.setup()
    build = allocator.allocate()
    allocator.provision(build)
    info = build.to_json()
    # Print the build_unit info
    click.echo(info)
