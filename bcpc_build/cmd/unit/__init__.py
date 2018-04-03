from bcpc_build.build_unit import BuildLogger
from bcpc_build.build_unit import BuildUnit
from bcpc_build.build_unit import BuildUnitAllocator
from bcpc_build.cmd.exceptions import CommandNotImplementedError
from bcpc_build.db import utils
from bcpc_build.db.migration_types import BuildStateEnum
from .config import cli as config_cli
from pathlib import Path
from terminaltables import AsciiTable
import abc
import click
import os
import shlex
import sqlalchemy as sa
import subprocess
import sys
try:
    import simplejson as json
except ImportError:
    import json
from json import JSONEncoder


class NotFoundError(click.ClickException):
    def __init__(id, *args, **kwargs):
        super().__init__("No such unit with id '%s'" % id)


### formatters ###
class DisplayFormat(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def format(cls, data, **kwargs):
        """Generally a list of objects."""
        raise NotImplementedError(cls.__name__)


class ListingFormat(DisplayFormat):
    pass


class ShowFormat(DisplayFormat):
    pass


class BuildUnitShowJSONFormat(ShowFormat):
    @classmethod
    def format(cls, data, **kwargs):
        return data.to_json()


class BuildUnitShowTableFormat(ShowFormat):
    HEADER_ROW = ('Property', 'Value')

    @classmethod
    def format(cls, data, **kwargs):
        long = kwargs.get('long', False)
        header = cls.HEADER_ROW

        def render(obj):
            from collections import OrderedDict as odict
            attrs = obj._attrs_
            return odict([(k, str(getattr(obj, k))) for k in attrs])

        def generate_tdata(_data):
            return [header] + [(k, v) for k, v in render(_data).items()]

        tdata = generate_tdata(data)
        table = AsciiTable(tdata)
        return table.table


class BuildUnitListingTableFormat(ListingFormat):
    SHORT_HEADER_ROW = ('id', 'build_dir', 'name', 'updated_at', 'build_state')
    LONG_HEADER_ROW = list(BuildUnit._attrs_) + [
        'created_at', 'updated_at', 'build_state'
    ]

    @classmethod
    def format(cls, data, **kwargs):
        long = kwargs.get('long', False)
        header = cls.LONG_HEADER_ROW if long else cls.SHORT_HEADER_ROW

        def render_row(obj):
            return tuple([str(getattr(obj, k)) for k in header])

        def generate_tdata(_data):
            import builtins
            rows = [header]
            data_rows = builtins.list(map(lambda x: render_row(x), _data))
            rows += sorted(data_rows, key=lambda r: r[-1])
            return rows

        tdata = generate_tdata(data)
        table = AsciiTable(tdata)
        return table.table


class BuildUnitListingJSONFormat(ListingFormat):
    class BuildUnitEncoder(object):
        @staticmethod
        def default(obj):
            if isinstance(obj, BuildUnit):
                return BuildUnit.get_json_dict(obj)
            else:
                return obj

    @classmethod
    def format(cls, data, **kwargs):
        BuildUnitEncoder = BuildUnitListingJSONFormat.BuildUnitEncoder
        return json.dumps(data, default=BuildUnitEncoder.default, indent=2)


@click.group(help='Manages build units.')
@click.pass_context
def cli(ctx):
    pass


@cli.command(help='Initiate a build of a unit.')
@click.pass_context
@click.option('--wait/--no-wait', default=False,
              help='Wait for build synchronously.')
@click.option('--strategy', help='Build strategy.',
              type=click.Choice(BuildUnitAllocator.BUILD_STRATEGY_NAMES),
              required=True)
@click.argument('id')
def build(ctx, wait, strategy, id):
    if not wait:
        raise CommandNotImplementedError('build --no-wait')
    sa_errors = (sa.orm.exc.NoResultFound,
            sa.orm.exc.NoResultFound)
    conf = dict(strategy=strategy)
    try:
        bunit = None
        allocator = BuildUnitAllocator.get_allocator(conf)
        # use id or name
        try:
            md = BuildUnit.metadata
            sa_type = type(md.tables[BuildUnit.__tablename__].c.id.type)
            sa_type._coerce(id)
            bunit = allocator.session.query(BuildUnit).get(id)
        except ValueError as e:
            allocator.logger.debug('Attempting BuildUnit lookup by name.')
        except Exception:
            allocator.logger.debug('Some error occurred: %s' % e)

        if not bunit:
            try:
                q = allocator.session.query(BuildUnit).filter_by(name=id)
                bunit = q.one()
            except sa_errors as e:
                raise NotFoundError(id) from e

        build_seq = allocator.build(bunit)
        blog = allocator.get_build_log(bunit)
        log_args = dict(filename=blog)
        if wait:
            log_args['func'] = click.echo

        blogger = BuildLogger(**log_args)
        try:
            while True:
                blogger.echo(next(build_seq))
        except StopIteration:
            allocator.set_build_state(bunit, BuildStateEnum.done)
            click.echo('Build complete.')
    except click.ClickException:
        raise


@cli.command(help='Show build unit information.')
@click.pass_context
@click.argument('id')
@click.option('--format', help='Display format', default='table')
def show(ctx, id, format):
    formatters = {
        'json': BuildUnitShowJSONFormat,
        'table': BuildUnitShowTableFormat,
    }
    session = utils.Session()
    try:
        bunit = session.query(BuildUnit).get(id)
        if bunit is None:
            msg = "No such unit with id '%s'" % id
            raise click.ClickException(msg)
        formatter = formatters[format]
        click.echo(formatter.format(bunit))
    except sa.exc.SQLAlchemyError as e:
        raise click.ClickException(e)
    except KeyError:
        raise NotImplementedError('%s format' % format)


@cli.command(help='Start a shell in the build unit.')
@click.pass_context
@click.argument('id')
def shell(ctx, id):
    CalledProcessError = subprocess.CalledProcessError
    sh = '/bin/bash'
    env = {
        'SHELL': sh,
    }

    def _envargs():
        pairs = ["%s='%s'" % (k, env[k]) for k in env.keys()]
        return ' '.join(pairs)

    cmdlist = [
        "env {envargs} sudo -n -p 'Password for %p' login -f {user}",
        "su -c 'login -f {user}'",
        "env {envargs} sudo -p 'Password for %u' -u {user} -",
    ]
    session = utils.Session()
    try:
        bunit = session.query(BuildUnit).get(id)
        user = bunit.build_user
        for c in cmdlist:
            r = 0
            cmd = shlex.split(c.format(user=user, envargs=_envargs()))
            r = subprocess.call(cmd)
            if r == 0:
                break
        if r != 0:
            msg = ('Could not spawn shell:'
                   ' "{cmd}" returned with non-zero status {ret}'.format(
                       cmd=' '.join(cmd), ret=r))
            click.echo(msg, err=True)
    except sa.exc.SQLAlchemyError:
        click.echo("No such unit with id '%s'" % id, err=True)


@cli.command(help='Destroy build unit.')
@click.pass_context
@click.argument('id')
def destroy(ctx, id):
    sa_errors = (sa.orm.exc.NoResultFound,
            sa.orm.exc.NoResultFound)
    try:
        bunit = None
        allocator = BuildUnitAllocator()
        # use id or name
        try:
            md = BuildUnit.metadata
            sa_type = type(md.tables[BuildUnit.__tablename__].c.id.type)
            sa_type._coerce(id)
            bunit = allocator.session.query(BuildUnit).get(id)
        except ValueError as e:
            allocator.logger.debug('Attempting BuildUnit lookup by name.')
        except Exception:
            allocator.logger.debug('Some error occurred: %s' % e)

        if not bunit:
            try:
                q = allocator.session.query(BuildUnit).filter_by(name=id)
                bunit = q.one()
            except sa_errors as e:
                raise NotFoundError(id) from e
        allocator.destroy(bunit)
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(e)
        raise click.Abort


@cli.command(help='List build units.')
@click.pass_context
@click.option('--format', '-f', help='Listing format', default='table')
@click.option('--long', help='List all fields', is_flag=True, default=False)
def list(ctx, format, long):
    import builtins
    formatters = {
        'json': BuildUnitListingJSONFormat,
        'table': BuildUnitListingTableFormat,
    }
    session = utils.Session()
    try:
        builds = session.query(BuildUnit)

        if not builtins.list(builds):
            return
        formatter = formatters[format]
        click.echo(formatter.format(sorted(builds), long=long))
    except sa.exc.SQLAlchemyError as e:
        click.echo('Something went wrong: %s' % e, err=True)
        raise click.Abort
    except KeyError:
        raise NotImplementedError('%s format' % format)

@cli.command(help='Modify build unit metadata')
@click.pass_context
@click.argument('id')
@click.option('--set-state', help='Set build unit state.',
              type=click.Choice(BuildStateEnum.__members__.keys()),
              metavar='BUILDSTATE')
def modify(ctx, set_state, id):
    sa_errors = (sa.orm.exc.NoResultFound,
                sa.orm.exc.NoResultFound)
    try:
        bunit = None
        allocator = BuildUnitAllocator()
        # use id or name
        try:
            md = BuildUnit.metadata
            sa_type = type(md.tables[BuildUnit.__tablename__].c.id.type)
            sa_type._coerce(id)
            bunit = allocator.session.query(BuildUnit).get(id)
        except ValueError as e:
            allocator.logger.debug('Attempting BuildUnit lookup by name.')
        except Exception:
            allocator.logger.debug('Some error occurred: %s' % e)

        if not bunit:
            try:
                q = allocator.session.query(BuildUnit).filter_by(name=id)
                bunit = q.one()
            except sa_errors as e:
                raise NotFoundError(id) from e

        if set_state:
            state_obj = getattr(BuildStateEnum, set_state)
            allocator.set_build_state(bunit, state_obj)
    except click.ClickException:
        raise


cli.add_command(config_cli, name='config')
