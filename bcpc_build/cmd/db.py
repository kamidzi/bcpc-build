from bcpc_build import config
from .exceptions import CommandNotImplementedError
import click


@click.group(help='Administers the database.')
@click.pass_context
def cli(ctx):
    pass


@cli.command(help="Setups up the database.")
@click.option('--force', is_flag=True,
              help='Force initial setup even if previously run.')
@click.pass_context
def setup(ctx, force):
   raise CommandNotImplementedError('setup')


@cli.command(help="Migrates the database.")
@click.pass_context
def migrate(ctx):
   raise CommandNotImplementedError('migrate')


@cli.command(help="Opens interactive console into database.")
@click.pass_context
def console(ctx):
   raise CommandNotImplementedError('console')
