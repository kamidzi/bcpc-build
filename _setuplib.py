# https://gist.github.com/zeroslack/4175259ab36ab86d76ab08c88ddf37b4
from glob import glob
import contextlib
import copy
import importlib.util
import os
import os.path
import platform
import shlex
import shutil
import subprocess
import tempfile
import warnings
import weakref
import zipfile

from lxml import html
import certifi
import requests

try:
    from contextlib import nullcontext
except ImportError:

    @contextlib.contextmanager
    def nullcontext(enter_result=None):
        if enter_result is None:
            yield
        else:
            yield enter_result


class SDKDownloader:
    # N.B. - needs trailing slash in case of expansion with relative dir link
    BASE_URL = 'https://download.virtualbox.org/virtualbox/'
    sdk_regex = r".*SDK-{ver}.*\.zip$"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.cacert = None
        # TODO: setup a partial to always include cert

    def resolve_absolute_href(self, elem, base_url=BASE_URL):
        elem = copy.copy(elem)
        elem.make_links_absolute(base_url)
        return elem.get('href')

    def find_latest_stable_version(self, tree):
        links = tree.xpath('//a[.="LATEST-STABLE.TXT"]')
        assert len(links) == 1
        elem = links.pop()
        url_latest = self.resolve_absolute_href(elem)
        return self.get(url_latest).text.strip()

    # https://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py
    @contextlib.contextmanager
    def download_file(self, url, keep=True, **kwargs):
        if keep:
            cm = nullcontext(tempfile.mkdtemp())
        else:
            cm = tempfile.TemporaryDirectory()

        with cm as tmpdir:
            try:
                local_filename = os.path.join(tmpdir, url.split('/')[-1])
                r = self.get(url, stream=True)
                try:
                    with open(local_filename, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                except OSError as e:
                    raise RuntimeError(
                        'Download of "{}" to {} failed'
                        ''.format(url, local_filename)
                    ) from e

                yield os.path.abspath(local_filename)
            finally:
                pass

    @staticmethod
    @contextlib.contextmanager
    def cacert_path(delete=True):
        glob_patterns = ['*.crt', '*.pem']
        kwargs_ = dict(delete=delete)
        try:
            ssl_cert_dir = os.environ.get('SSL_CERT_DIR', None)
            if ssl_cert_dir is not None:

                def _get_paths():
                    for pat in glob_patterns:
                        glob_ = os.path.join(ssl_cert_dir, pat)
                        yield from glob(glob_)

                with tempfile.NamedTemporaryFile('w', **kwargs_) as certfile:
                    with open(certifi.where()) as existing_certs:
                        certfile.write(existing_certs.read())

                    for cert in _get_paths():
                        try:
                            with open(cert) as fh:
                                certfile.write(fh.read())
                        except OSError as e:
                            raise RuntimeError(
                                'Could not add certificate {}.'.format(cert)
                            ) from e
                    certfile.flush()
                    yield certfile.name
            else:
                yield certifi.where()
        finally:
            pass

    def get(self, url, **kwargs):
        kwargs.setdefault('verify', self.cacert)
        return requests.get(url, **kwargs)

    @contextlib.contextmanager
    def run(self, keep_files=False):
        try:
            if os.environ.get('SSL_CERT_DIR', None) is not None:
                # TODO(kmidzi): need to cache
                with self.__class__.cacert_path(delete=False) as path:
                    self.cacert = path
                    weakref.finalize(self, os.unlink, path)
            else:
                # This toggles based upon SSL_CERT_DIR
                self.cacert = None

            resp = self.get(self.base_url)
            tree = html.fromstring(resp.content)
            ver = self.find_latest_stable_version(tree)
            dir_url = self.resolve_absolute_href(
                tree.xpath('//a[.="{}/"]'.format(ver)).pop()
            )
            content = self.get(dir_url).content
            tree = html.fromstring(content)

            regex = self.sdk_regex.format(ver=ver)
            sdk_elem = tree.xpath(
                '//a[re:match(text(), "{regex}")]'.format(regex=regex),
                namespaces={"re": "http://exslt.org/regular-expressions"},
            ).pop()
            sdk_url = self.resolve_absolute_href(sdk_elem, dir_url)
            with self.download_file(sdk_url, keep=keep_files) as artifact:
                yield artifact
        finally:
            pass


if platform.system() == 'Linux':
    _install_path = '/usr/lib/virtualbox'
    _env = dict(VBOX_INSTALL_PATH=_install_path)
else:
    _env = {}


@contextlib.contextmanager
def env(**kwds):
    oldenv = os.environ.copy()
    try:
        os.environ.update(kwds)
        yield
    finally:
        os.environ = oldenv


@contextlib.contextmanager
def chdir(path):
    try:
        cwd = os.path.abspath(os.curdir)
        os.chdir(path)
        yield cwd
    finally:
        os.chdir(cwd)


class VBoxAPIInstaller:
    @staticmethod
    def run(archive):
        with tempfile.TemporaryDirectory() as tmpdir:
            with chdir(tmpdir):
                files = os.listdir(os.curdir)
                fp = zipfile.ZipFile(archive)
                fp.extractall()

                newls = os.listdir(os.curdir)
                newdir = (set(newls) - set(files)).pop()

                def setup():
                    # run the setup
                    with chdir(os.path.join(newdir, 'installer')):
                        setup_file = 'vboxapisetup.py'
                        cmd = 'python {} install'.format(setup_file)
                        with env(**_env):
                            proc = subprocess.Popen(
                                shlex.split(cmd), stdout=subprocess.PIPE
                            )
                            for line in iter(
                                lambda: proc.stdout.readline(), b''
                            ):
                                print(line.decode('utf-8'), end='')
                            ret = proc.wait()
                        if ret != 0:
                            raise RuntimeError('Installation failed!')

                setup()

    @staticmethod
    def installation_test():
        _module = None
        try:
            _module = importlib.import_module('virtualbox')

            def test_method():
                vbox = _module.VirtualBox()
                vbox.system_properties

        except ImportError:

            def test_method():
                _module = importlib.import_module('vboxapi')
                _module.VirtualBoxManager(None, None)

        try:
            test_method()
        except Exception as e:
            modname = _module.__file__ if _module is not None else 'vboxapi'
            warnings.warn('ERROR Using {}: {}'.format(modname, e))
