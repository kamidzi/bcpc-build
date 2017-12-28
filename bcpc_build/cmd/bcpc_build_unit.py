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

@cli.command()
def build(source_url):
    allocator = BuildUnitAllocator()
    allocator.setup()
    build = allocator.allocate()
    allocator.provision(build)
    click.echo(build.to_json())

@cli.command()
@click.option('--format', help='Listing format')
def list(format):
    pass

if __name__ == '__main__':
    cli()
