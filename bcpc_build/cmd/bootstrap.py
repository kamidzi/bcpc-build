from bcpc_build.build_unit import BuildUnitAllocator
from bcpc_build.cmd.exceptions import CommandNotImplementedError
from bcpc_build.exceptions import AllocationError
import click
import shlex
import subprocess
import sys
try:
    import simplejson as json
except ImportError:
    import json


@click.command(help='Bootstraps a new build.')
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
    try:
        build = allocator.allocate()
        allocator.provision(build)
        info = json.loads(build.to_json())
    except AllocationError as e:
        allocator._deallocate(build)

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
            if status == 0:
                sys.exit(0)
            elif status < 0:
                sys.exit('Build process killed with'
                         ' signal %d' % (-1*status))
            else:
                sys.exit('Build process exited with'
                         ' status %d' % status)

        while True:
            output = proc.stdout.readline().strip()
            status = proc.poll()
            if output == '' and status is not None:
                handle_status(status)
            if output:
                print(output)
        click.echo(json.dumps(info, indent=2))

    do_bootstrap(info)
