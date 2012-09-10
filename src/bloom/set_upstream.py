# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import sys
import os

try:
    from vcstools import VcsClient
except ImportError:
    print("vcstools was not detected, please install it.", file=sys.stderr)
    sys.exit(1)

from bloom.util import maybe_continue, execute_command, bailout, ansi
from bloom.util import get_current_git_branch, error


def usage():
    """Prints usage message"""
    print("""\
usage: git bloom set-upstream <upstream-repo> <upstream-repo-type> \
[<upstream-repo-branch>]

Creates (if necessary) an orphan branch "bloom" in the current gbp repo
and sets the upstream repo and type in the bloom.conf.  The rest of the
bloom utilities pivot off of these values.
""")


def check_git_init():
    cmd = 'git show-ref --heads'
    result = execute_command(cmd, shell=True, autofail=False)
    if result != 0:
        print("Freshly initialized git repository detected.")
        print("An initial empty commit is going to be made.")
        if not maybe_continue():
            bailout("Exiting.")
        # Make an initial empty commit
        execute_command('git commit -m "initial commit" --allow-empty')


def set_upstream(bloom_repo, upstream_repo, upstream_repo_type,
                 upstream_repo_branch):
    # Check for freshly initialized repo
    check_git_init()

    # Check for a bloom branch
    if execute_command('git show-branch origin/bloom', autofail=False) == 0:
        # Found a bloom branch
        print("Found a remote bloom branch, checking out.")
        # Check out the bloom branch
        bloom_repo.update('bloom')
    else:
        # No bloom branch found, create one
        execute_command('git symbolic-ref HEAD refs/heads/bloom')
        execute_command('rm -f .git/index')
        execute_command('git clean -fdx')
        execute_command('git commit --allow-empty -m "Initial bloom branch"')

    # Now set the upstream using the bloom config
    cmd = 'git config -f bloom.conf bloom.upstream "{0}"'.format(upstream_repo)
    execute_command(cmd)
    cmd = 'git config -f bloom.conf ' \
        + 'bloom.upstreamtype "{0}"'.format(upstream_repo_type)
    execute_command(cmd)
    cmd = 'git config -f bloom.conf ' \
        + 'bloom.upstreambranch "{0}"'.format(upstream_repo_branch)
    execute_command(cmd)

    execute_command('git add bloom.conf')
    cmd = 'git commit -m "bloom branch update by git-bloom-set-upstream"'
    execute_command(cmd)


def summarize_arguments(upstream_repo, upstream_repo_type,
                        upstream_repo_branch):
    # Summarize the requested operation
    summary_msg = "Upstream " + ansi('boldon') + upstream_repo
    summary_msg += ansi('boldoff') + " type: " + ansi('boldon')
    summary_msg += upstream_repo_type + ansi('boldoff')
    print(summary_msg)


def validate_args(bloom_repo, upstream_repo_type):
    # Check that the current directory is a servicable git/bloom repo
    if not bloom_repo.detect_presence():
        error("Not in a git repository.\n")
        return False

    # Ensure that the upstream-repo-type is valid
    if upstream_repo_type not in ['git', 'svn', 'hg', 'bzr']:
        error("Invalid upstream repository type: "
              "{0}\n".format(upstream_repo_type))
        return False
    return True


def main():
    # Ensure we have the corrent number of arguments
    if len(sys.argv) not in [3, 4]:
        usage()
        return 1

    # Gather command line arguments into variables
    upstream_repo = sys.argv[1]
    upstream_repo_type = sys.argv[2]
    if len(sys.argv) == 4:
        upstream_repo_branch = sys.argv[3]
    else:
        upstream_repo_branch = None

    # Create vcs client
    bloom_repo = VcsClient('git', os.getcwd())

    # Summarize the requested operation
    summarize_arguments(upstream_repo, upstream_repo_type,
                        upstream_repo_branch)

    # Validate the arguments and repository
    if not validate_args(bloom_repo, upstream_repo_type):
        usage()
        return 1

    # Store the current branch
    current_branch = get_current_git_branch()
    try:
        set_upstream(bloom_repo, upstream_repo, upstream_repo_type,
                     upstream_repo_branch)
        print("Upstream successively set.")
        return 0
    finally:
        # Try to roll back to the branch the user was on before
        # this possibly failed.
        if current_branch:
            bloom_repo.update(current_branch)

    return 1
