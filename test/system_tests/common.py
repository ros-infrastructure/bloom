"""
Common tools for system tests
"""

from __future__ import print_function

import os

from ..utils.common import bloom_answer
from ..utils.common import change_directory
from ..utils.common import user


def create_release_repo(upstream_url, upstream_type, upstream_branch='',
                        rosdistro='indigo'):
    user('mkdir foo_release')
    with change_directory('foo_release'):
        user('git init .')
        answers = ['y', 'foo', upstream_url, upstream_type,
                   '', '', upstream_branch, rosdistro]
        with bloom_answer(answers):
            user('git-bloom-config new ' + str(rosdistro))
        url = 'file://' + os.getcwd()
    return url
