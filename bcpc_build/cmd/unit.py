from bcpc_build.build_unit import BuildUnitAllocator
from bcpc_build.build_unit import NotImplementedError
from bcpc_build.build_unit import BuildUnit
from bcpc_build.db import utils
from terminaltables import AsciiTable
import click
import abc
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
            return [header] + [(k,v) for k,v in render(_data).items()]

        tdata = generate_tdata(data)
        table = AsciiTable(tdata)
        return table.table


class BuildUnitListingTableFormat(ListingFormat):
    SHORT_HEADER_ROW = ('id', 'build_dir')
    LONG_HEADER_ROW = BuildUnit._attrs_

    @classmethod
    def format(cls, data, **kwargs):
        long = kwargs.get('long', False)
        header = cls.LONG_HEADER_ROW if long else cls.SHORT_HEADER_ROW

        def render_row(obj):
            return tuple([str(getattr(obj, k)) for k in header])

        def generate_tdata(_data):
            import builtins
            return [header] + builtins.list(map(lambda x: render_row(x), _data))

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
@click.option('--source-url', help='Source url for the build.', required=True)
def build(ctx, source_url):
    allocator = BuildUnitAllocator()
    allocator.setup()
    build = allocator.allocate()
    allocator.provision(build)
    click.echo(build.to_json())


@cli.command(help='Show build unit information')
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
        formatter = formatters[format]
        click.echo(formatter.format(bunit))
    except sa.exc.SQLAlchemyError:
        click.echo("No such unit with id '%s'" % id, err=True)
    except KeyError:
        raise NotImplementedError('%s format' % format)

@cli.command(help='List build units')
@click.pass_context
@click.option('--format', help='Listing format', default='table')
@click.option('--long', help='List all fields', is_flag=True, default=False)
def list(ctx, format, long):
    import builtins
    formatters = {
        'json': BuildUnitListingJSONFormat,
        'table': BuildUnitListingTableFormat,
    }
    session = utils.Session()
    builds = session.query(BuildUnit)

    if not builtins.list(builds):
        return
    try:
        formatter = formatters[format]
    except KeyError:
        raise NotImplementedError('%s format' % format)
    click.echo(formatter.format(sorted(builds), long=long))
