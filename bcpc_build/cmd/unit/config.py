from bcpc_build.build_unit import BuildUnit
from bcpc_build.cmd.exceptions import CommandNotImplementedError
from bcpc_build.db import utils
from pathlib import Path
import click
import sqlalchemy as sa
import subprocess
try:
    import simplejson as json
except ImportError:
    import json


CONFIG_SHOW_FMTS = ['shell', 'json']


@click.group(help='Manages build unit configuration.')
@click.pass_context
def cli(ctx):
    pass


@cli.command(help='Synchronizes configuration.')
@click.pass_context
@click.argument('id', type=click.UUID)
def sync(ctx, id):
    raise CommandNotImplementedError('sync')


@cli.command(help='Show active configuration')
@click.option('--format', help='Format to display data',
              type=click.Choice(CONFIG_SHOW_FMTS), default='shell')
@click.pass_context
@click.argument('id', type=click.UUID)
def show(ctx, format, id):
    def _get_script_dir(bunit):
        bdir = Path(bunit.build_dir)
        return (bdir / 'chef-bcpc' / 'bootstrap/vagrant_scripts').as_posix()

    session = utils.Session()
    try:
        bunit = session.query(BuildUnit).get(id)
        if not bunit:
            raise NotFoundError(id)
        sdir = _get_script_dir(bunit)
        out = subprocess.check_output('./dump_config.sh', cwd=sdir,
                                      universal_newlines=True)
        out = '\n'.join(filter(lambda x: x.strip(), out.split('\n')))

        def _mk_json(out):
            lines = sorted(out.split('\n'))
            try:
                d = {}
                for l in lines:
                    parts = l.split('=')
                    key = parts[0]
                    value = ''.join(parts[1:])
                    d[key] = value
                return json.dumps(d, indent=2, sort_keys=True)
            except IndexError:
                raise click.ClickException('Malformed configuration.')

        if format == 'json':
            out = _mk_json(out)
        click.echo(out)
    except sa.exc.SQLAlchemyError as e:
        click.echo('Something went wrong: %s' % e, err=True)
        raise click.Abort


@cli.command(help='Edit current configuration.')
@click.option('--set', help='Set an option', is_flag=True)
@click.option('--delete', help='Delete an option', is_flag=True)
@click.pass_context
@click.argument('id', type=click.UUID)
def edit(ctx, set, delete, id):
    if set:
        raise CommandNotImplementedError('--set')
    if delete:
        raise CommandNotImplementedError('--delete')
    raise CommandNotImplementedError('Interactive configuration editing')
