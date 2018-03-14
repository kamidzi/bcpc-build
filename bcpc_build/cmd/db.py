from alembic.config import Config
from alembic import command
from bcpc_build.db import utils as dbutils
from bcpc_build import config
from .exceptions import CommandNotImplementedError
from pathlib import Path
import bcpc_build
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
    # TODO: change this
    p = Path(bcpc_build.__file__)
    pkg_dir = p.parent.parent
    config_file = pkg_dir.joinpath('alembic.ini').as_posix()
    # TODO(kamidzi): check for file
    alembic_cfg = Config(config_file)
    alembic_cfg.set_section_option('alembic', 'sqlalchemy.url', config.db.url)
    command.upgrade(alembic_cfg, 'head')


@cli.command(help="Migrates the database.")
@click.pass_context
def migrate(ctx):
   raise CommandNotImplementedError('migrate')


@cli.command(help="Backup the database.")
@click.option('--destination', help='URI for destination.', required=True)
@click.pass_context
def backup(ctx, destination):
    try:
        dbutils.backup(destination)
    except dbutils.BackupError as e:
        click.echo(e, err=True)


@cli.command('import', help="Import the database.")
@click.option('--backup/--no-backup', default=True,
              help="Backup current database during import.")
@click.argument('uri')
@click.pass_context
def import_db(ctx, backup, uri):
    dest = dbutils.get_backup_uri()
    try:
        try:
            if backup:
                dbutils.backup(dest)
        except dbutils.NoBackupSource:
            pass
        dbutils.import_db(uri)
    except Exception as e:
        click.echo('Could not import database: %s' % e, err=True)
        raise click.Abort()


@cli.command(help="Opens interactive console into database.")
@click.pass_context
def console(ctx):
    dbutils.start_console(config.db.url)
