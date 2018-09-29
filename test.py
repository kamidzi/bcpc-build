#!/usr/bin/env python3
import os
import urllib.parse
import sys
import re

logger = lambda x: None
logger.info = lambda x: None
logger.debug = lambda x: None

BUILD_SRC_URL = os.environ.get('BUILD_SRC_URL')
if not BUILD_SRC_URL:
    sys.exit('export BUILD_SRC_URL')

build_path = 'build_path'
def populate_build_unit(name):
    logger.info('Populating build unit...')
    src_url = BUILD_SRC_URL
    def git_args(url):
        regex = r'/tree/(?P<branch>.*)$'
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        # Translate branch url to git arguments
        args = {}
        args['git'] = '-C %s' % build_path
        args['url'] = url
        try:
            path, branch = path.split('/tree/')
            logger.debug('Detected branch %s from source url' % branch)
            args['clone'] = '-b %s' % branch
            # replace the path to exclude branch
            u = parsed._replace(path=path)
            clean_url = urllib.parse.urlunparse(u)
            args['url'] = clean_url
        except (AttributeError, ValueError) as e:
            logger.debug(e)
        return args

    args = git_args(src_url)
    cmd = ("su -c 'git {git_args} clone {clone_args} {url}' "
           "{username}").format(git_args=args.get('git', ''),
                                clone_args=args.get('clone', ''),
                                url=args.get('url'),
                                username=name)
    print(cmd)

def git_args(url):
    regex = r'/tree/(?P<branch>.*)$'
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    # Translate branch url to git arguments
    m = re.search(regex, path)
    try:
        branch = m.group('branch')
        return '-b %s' % branch
    except (AttributeError, IndexError) as e:
        return ''


if __name__ == '__main__':
    populate_build_unit('foo')

