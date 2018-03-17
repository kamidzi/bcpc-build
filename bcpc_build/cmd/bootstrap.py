from bcpc_build.build_unit import BuildUnitAllocator
from bcpc_build.build_unit import DEFAULT_ALLOCATOR
from bcpc_build.cmd.exceptions import CommandNotImplementedError
from bcpc_build.exceptions import AllocationError
from bcpc_build.exceptions import ProvisionError
from configparser import ConfigParser
import click
import shlex
import subprocess
import sys
try:
    import simplejson as json
except ImportError:
    import json


@click.command(help='Bootstraps a new build.')
@click.option('--config-file', '-c', type=click.File(),
              help='Config file for bootstrap operation.')
@click.option('--source-url', help='URL for build sources.')
@click.option('--depends', help='Source dependency <name>:<url>',
              multiple=True, default=[])
@click.option('--strategy',
              help='Build strategy.',
              type=click.Choice(BuildUnitAllocator.BUILD_STRATEGY_NAMES),
              default=BuildUnitAllocator.BUILD_STRATEGY_DEFAULT)
@click.option('--configure/--no-configure', default=True,
              help='Run the configuration phase.')
@click.option('--build/--no-build', default=True,
              help='Run the build phase.')
@click.option('--wait/--no-wait', default=False,
              help='Wait for bootstrap to complete in foreground.')
@click.pass_context
@click.argument('name', default='')
def bootstrap(ctx, config_file, source_url, depends,
              strategy, configure, build, wait, name):
    def _parse_conf(conffile):
        cfg = ConfigParser()
        cfg.read_file(conffile)
        ret = {}
        for k, sect in cfg.items():
            ret[k] = dict(sect.items())
        return ret

    def _parse_depends(lst):
        SEP = '='
        pairs = []
        for spec in lst:
            spec = spec.strip()
            if spec:
                k, u = spec.split(SEP)
                pairs.append((k,u))
        return dict(pairs or {})

    # TODO(kamidzi): do this properly
    # Get the bootstrap config and move DEFAULT keys to toplevel with other
    # params from click context
    conf = ctx.params.copy()
    _conf = _parse_conf(config_file) if config_file else {}
    conf.update(_conf.pop('DEFAULT', {}))
    conf.update(_conf)
    if depends and not depends[0].startswith('--'):
        conf['src_depends'] = _parse_depends(depends)
    if not wait:
        raise CommandNotImplementedError('bootstrap --no-wait')
    allocator = BuildUnitAllocator.get_allocator(conf=conf)
    allocator.setup()
    try:
        if not source_url:
            source_url = allocator.DEFAULT_SRC_URL
        build = allocator.allocate(source_url=source_url, name=name)
        allocator.provision(build, conf=conf)
        info = json.loads(build.to_json())
        click.echo(json.dumps(info, indent=2))
        # do the build
        if conf['build']:
            build_seq = allocator.build(build)
            try:
                while True:
                    click.echo(next(build_seq))
            except StopIteration:
                click.echo('Bootstrap complete.')
    except (AllocationError, ProvisionError) as e:
        click.echo('Rolling back changes...') 
        allocator.destroy(build, commit=True)
        raise click.ClickException(e)
