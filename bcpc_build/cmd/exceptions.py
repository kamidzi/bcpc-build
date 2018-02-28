import click

class Abort(click.Abort):
    def __init__(msg, *args, **kwargs):
        click.echo('Some error occurred: %s' % msg, err=True)
        super().__init__()
