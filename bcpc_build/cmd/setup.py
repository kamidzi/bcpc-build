from bcpc_build import config
from pathlib import Path
import click
import shlex
import subprocess
import sys

@click.command()
@click.option('--force', is_flag=True,
              help='Force initial setup even if previously run.')
@click.pass_context
def init(ctx, force):
    """Initializes the bcpc-build installation."""
    def _mk_user_conf_dir(force=False):
        path = Path.home().joinpath(config.USER_CONF_DIRNAME)
        mode = 0o0741
        try:
            path.mkdir(mode, exist_ok=True)
        except FileExistsError as e:
            sys.exit(click.echo('Some error occurred: %s' % e, err=True))
        return path

    def _create_conf(dirpath, force=False):
        mode = 0o0600
        path = dirpath.joinpath(config.USER_CONF_FILENAME)
        try:
            path.touch(mode, exist_ok=force)
        except FileExistsError as e:
            sys.exit(click.echo('Some error occurred: %s' % e, err=True))
        return path.as_posix()

    d = _mk_user_conf_dir(force)
    _create_conf(d, force)


@click.command()
@click.pass_context
def setup(ctx):
    pass
