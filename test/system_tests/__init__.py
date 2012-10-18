"""
Common tools for system tests
"""

from __future__ import print_function

import os

from ..utils import bloom_answer
from ..utils import change_directory
from ..utils import user


def create_release_repo(upstream_url, upstream_type, upstream_branch=''):
    user('mkdir foo_release')
    with change_directory('foo_release'):
        user('git init .')
        cmd = 'git-bloom-config'
        with bloom_answer('y'):
            user(' '.join([cmd, upstream_url, upstream_type, upstream_branch]))
        url = 'file://' + os.getcwd()
    return url
