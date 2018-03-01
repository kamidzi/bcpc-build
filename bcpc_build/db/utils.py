from bcpc_build import config
from datetime import datetime
from furl import furl
from pathlib import Path
from shutil import copyfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from subprocess import call
import os.path


# TODO: make configurable
engine = create_engine(config.db.url)
Session = sessionmaker(bind=engine)

def start_console(url):
    """Starts a db-specific console."""
    uri = furl(url)
    scheme = uri.scheme

    if scheme == 'sqlite':
        args = ['sqlite3', '-bail', str(uri.path.normalize())]
    else:
        raise NotImplementedError('db console for %s' % scheme)
    call(args)


def get_backup_uri():
    """Construct default backup destination."""
    url = furl(config.db.url)
    scheme = url.scheme
    if scheme == 'sqlite':
        suffix = '.bak.%s' % datetime.utcnow().timestamp()
        uri = config.db.url + suffix
    else:
        raise NotImplementedError('get_backup_uri() for %s' % scheme)
    return uri


def import_db(uri):
    dest_url = furl(config.db.url)
    src_url = furl(uri)
    dest_scheme = dest_url.scheme
    src_scheme = src_url.scheme
    # slqalchemy db urls
    def normalize_url_path(p):
        c = p.segments
        return os.path.sep.join(c)

    if dest_scheme == src_scheme == 'sqlite':
        a = normalize_url_path(src_url.path)
        src = Path(normalize_url_path(src_url.path))
        dest = Path(normalize_url_path(dest_url.path))
        copyfile(src.as_posix(), dest.as_posix())
    elif any([dest_scheme is None, src_scheme is None]):
        raise ValueError('scheme required in url string')
    else:
        raise NotImplementedError('import_db for %s' % scheme)


def backup(dest):
    """Backs up a database."""
    uri = furl(config.db.url)
    dest = furl(dest)
    scheme = uri.scheme

    if scheme == 'sqlite':
        src = str(uri.path.normalize())
        dest = str(dest.path.normalize())
        args = ['cp', '-p', src, dest]
    else:
        raise NotImplementedError('db backup for %s' % scheme)
    call(args)
