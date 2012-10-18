"""
These system tests are testing the release of fuerte catkin projects.
"""

from __future__ import print_function

import os
import sys

try:
    from vcstools import VcsClient
except ImportError:
    print("vcstools was not detected, please install it.", file=sys.stderr)
    sys.exit(1)

from . import create_release_repo

from ..utils import bloom_answer
from ..utils import change_directory
from ..utils import in_temporary_directory
from ..utils import user

from bloom.git import branch_exists
from bloom.git import get_branches
from bloom.git import inbranch

from bloom.util import code


def create_upstream_catkin_fuerte_repository(stack, directory=None):
    upstream_dir = 'upstream_repo_groovy'
    user('mkdir ' + upstream_dir)
    with change_directory(upstream_dir):
        user('git init .')
        user('echo "readme stuff" >> README.md')
        user('git add README.md')
        user('git commit -m "Initial commit"')
        user('git checkout -b fuerte_devel')
        stack_xml = """\
<stack>
  <name>{0}</name>
  <version>0.1.0</version>
  <description>
    ROS Stack named {0}
  </description>
  <author email="foo@bar.com">Foo Baz</author>
  <author>Ping Pong</author>
  <license>BSD</license>
  <copyright>Willow Garage</copyright>
  <url>http://www.ros.org/wiki/{0}</url>
  <build_type>python_distutils</build_type>

  <build_depends>catkin</build_depends>
</stack>
""".format(stack)
        with open('stack.xml', 'w+') as f:
            f.write(stack_xml)
        user('git add stack.xml')
        user('git commit -m "Releasing version 0.1.0"')
        user('git tag 0.1.0 -m "Releasing version 0.1.0"')
        url = 'file://' + os.getcwd()
    return url


@in_temporary_directory
def test_fuerte_package_repository(directory=None):
    """
    Release a single catkin stack (fuerte) repository.
    """
    directory = directory if directory is not None else os.getcwd()
    # Setup
    upstream_url = create_upstream_catkin_fuerte_repository('foo', directory)
    release_url = create_release_repo(upstream_url, 'git', 'fuerte_devel')
    release_dir = os.path.join(directory, 'foo_release_clone')
    release_client = VcsClient('git', release_dir)
    release_client.checkout(release_url)
    with change_directory(release_dir):
        ###
        ### Import upstream
        ###
        user('git-bloom-import-upstream --quiet')
        # does the upstream branch exist?
        assert branch_exists('upstream', local_only=True), "no upstream branch"
        # does the upstrea/0.1.0 tag exist?
        ret, out, err = user('git tag', return_io=True)
        assert out.count('upstream/0.1.0') == 1, "no upstream tag created"
        # Is the package.xml from upstream in the upstream branch now?
        with inbranch('upstream'):
            assert os.path.exists('stack.xml'), \
                   "upstream did not import: '" + os.getcwd() + "': " + \
                   str(os.listdir(os.getcwd()))
            assert open('stack.xml').read().count('0.1.0'), "not right file"

        ###
        ### Release generator
        ###
        with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
            ret = user('git-bloom-generate -y release -s upstream --quiet')
        # patch import should have reported OK
        assert ret == code.OK, "actually returned ({0})".format(ret)
        # do the proper branches exist?
        assert branch_exists('release/foo'), "no release/foo branch: " + \
                                             str(get_branches())
        assert branch_exists('patches/release/foo'), \
               "no patches/release/foo branch"
        # was the release tag created?
        ret, out, err = user('git tag', return_io=True)
        assert out.count('release/foo/0.1.0') == 1, "no release tag created"

        ###
        ### Release generator, again
        ###
        with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
            ret = user('git-bloom-generate -y release -s upstream --quiet')
        # patch import should have reported OK
        assert ret == code.OK, "actually returned ({0})".format(ret)
        # do the proper branches exist?
        assert branch_exists('release/foo'), "no release/foo branch: " + \
                                             str(get_branches())
        assert branch_exists('patches/release/foo'), \
               "no patches/release/foo branch"
        # was the release tag created?
        ret, out, err = user('git tag', return_io=True)
        assert out.count('release/foo/0.1.0') == 1, "no release tag created"
