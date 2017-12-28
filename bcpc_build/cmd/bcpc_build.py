from bcpc_build.build_unit import BuildUnitAllocator
import click
import shlex
import subprocess
import sys
try:
    import simplejson as json
except ImportError:
    import json


@click.group()
@click.pass_context
def cli(ctx):
    setattr(ctx, 'conf', {})


@cli.command(help='Bootstraps a new build.')
@click.pass_context
@click.option('--source-url', default=BuildUnitAllocator.DEFAULT_SRC_URL,
              help='URL for build sources.')
@click.option('--wait/--no-wait', default=False,
              help='Wait for bootstrap to complete in foreground.')
def bootstrap(ctx, source_url, wait):
    # TODO(kamidzi): do this properly
    conf = ctx.params.copy()
    allocator = BuildUnitAllocator(conf=conf)
    allocator.setup()
    build = allocator.allocate()
    allocator.provision(build)
    info = json.loads(build.to_json())

    def do_bootstrap(info):
        # Print the build_unit info
        click.echo(json.dumps(info, indent=2))
        cmd = ("su -c \"bash -c 'cd chef-bcpc/bootstrap/vagrant_scripts &&"
               " time ./BOOT_GO.sh'\" - {build_user}".format(**info))
        proc = subprocess.Popen(shlex.split(cmd),
                                stdout=subprocess.PIPE,
                                universal_newlines=True)

        # Need start_new_session to run in background?
        def handle_status(status):
            if status.returncode == 0:
                sys.exit(0)
            else:
                sys.exit('Build process exited with'
                         ' status %d' % status.returncode)

        while True:
            output = proc.stdout.readline().strip()
            status = proc.poll()
            if output == '' and status is not None:
                handle_status(status)
            if output:
                print(output)
        click.echo(json.dumps(info, indent=2))

    do_bootstrap(info)