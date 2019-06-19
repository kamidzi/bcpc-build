import logging
import sys
from itertools import chain


from furl import furl

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

bunit = lambda _: None
bunit.build_user = 'build_user'


def load_git_config():
    return {
        'https': {
            'proxy': 'http://someproxy.com'
        }
    }

build_path = '/fake/build/path'
conf = load_git_config()

def _load_creds(config):
    if 'filename' in config:
        # TODO(kamidzi): handle error and flesh out
        with open(config['filename']) as fp:
            raise NotImplementedError(
                'Loading credentials from filename not supported.'
            )


# FIXME(kamidzi): git-credential helper?
def git_args(url):
    url = furl(url)
    path = url.path
    scheme = url.scheme
    # Translate branch url to git arguments
    args = {}
    args['git'] = '-C %s' % build_path
    if scheme in conf:
        proxy = conf[scheme].get('proxy')
        if proxy:
            args['git'] += ' -c %s.proxy="%s"' % (scheme, proxy)

    if 'credentials' in conf:
        logger.debug('Detected credentials in configuration')
        creds = conf['credentials']
        url.set(username=creds['username'],
                password=creds['password'])
    args['url'] = url.url
    try:
        path, rev = str(path).split('/tree/')
        logger.debug('Detected branch %s from source url' % rev)
        args['revision'] = rev
        url.set(path=path)
        args['url'] = url.url
    except (ValueError,) as e:
        logger.debug('Revision/branch detection error: %s' % e)
    return args


def get_cmds(url, name):
    def _checkout_cmd(rev, dest):
        cmd = ("su -c"
                " 'git -C {dest} fetch origin {rev} &&"
                " git -C {dest} checkout FETCH_HEAD' "
                " {username}").format(rev=rev,
                                        username=bunit.build_user,
                                        dest=dest)
        logger.debug('Checkout cmd `{}` from rev={}'.format(cmd, rev))
        yield cmd

    def _clone_cmd(src_url, name=''):
        cmd = ("su -c 'git {git_args} clone {clone_args} {url} {name}' "
                "{username}").format(git_args=args.get('git', ''),
                                    clone_args=args.get('clone', ''),
                                    url=args.get('url'),
                                    name=name,
                                    username=bunit.build_user)
        logger.debug('Clone cmd `{}` from src_url={}'.format(cmd, src_url))
        yield cmd

    cmds = []
    args = git_args(url)
    cmds += _clone_cmd(url, name)
    rev = args.get('revision')
    if rev:
        dest = os.path.join(build_path, name)
        cmds += _checkout_cmd(rev, dest)
    return chain(cmds)


if __name__ == '__main__':
    bbgh = 'https://repo.example.com'
    print(git_args(bbgh))
    print(list(get_cmds(bbgh, 'chef-bcpc')))

