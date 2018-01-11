import click
import os
import shlex
import subprocess
import sys

@click.group(help='Initializes bcpc-build plumbing.')
@click.pass_context
def setup(ctx):
    pass
