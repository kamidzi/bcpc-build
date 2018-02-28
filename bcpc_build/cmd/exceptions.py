from bcpc_build import exceptions
import click

class Abort(click.Abort):
    def __init__(msg, *args, **kwargs):
        click.echo('Some error occurred: %s' % msg, err=True)
        super().__init__()


class CommandNotImplementedError(click.Abort, exceptions.NotImplementedError):
    _MESSAGE = '%s is not implemented!'

    def __init__(self, target, *args, **kwargs):
        self.message = self._MESSAGE % target
        click.echo(self.message, err=True)
        super().__init__()
