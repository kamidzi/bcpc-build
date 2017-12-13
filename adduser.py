#!/usr/bin/env python3
from subprocess import check_output
import os.path
import shlex
from bcpc_build import utils


if __name__ == '__main__':
    import sys

    try:
        username = sys.argv[1]
    except IndexError:
        sys.exit('Supply a username')

    utils.useradd(username)
