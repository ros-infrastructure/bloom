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

import os
import sys
import argparse

from . util import add_global_arguments
from . util import handle_global_arguments
from . util import maybe_continue, execute_command, ansi
from . logging import debug
from . logging import info
from . logging import error
from . git import branch_exists
from . git import checkout
from . git import create_branch
from . git import get_current_branch
from . git import get_root
from . git import has_changes
from . git import inbranch


def check_git_init():
    cmd = 'git show-ref --heads'
    result = execute_command(cmd, shell=True, autofail=False,
                             silent_error=True)
    if result != 0:
        info("Freshly initialized git repository detected.")
        info("An initial empty commit is going to be made.")
        if not maybe_continue():
            error("Answered no to continue, exiting.")
            return 1
        # Make an initial empty commit
        execute_command('git commit -m "initial commit" --allow-empty')
    return 0


def set_upstream(upstream_repo, upstream_repo_type, upstream_repo_branch):
    # Check for freshly initialized repo
    if check_git_init() != 0:
        return 1

    # Check for a bloom branch
    if branch_exists('bloom', False):
        # Found a bloom branch
        debug("Found a bloom branch, checking out.")
        # Check out the bloom branch
        checkout('bloom')
    else:
        # No bloom branch found, create one
        create_branch('bloom', changeto=True)

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
    if has_changes():
        cmd = 'git commit -m "bloom branch update by git-bloom-set-upstream"'
        execute_command(cmd)
    else:
        debug("No chages, nothing to commit.")


def summarize_arguments(upstream_repo, upstream_repo_type,
                        upstream_repo_branch):
    # Summarize the requested operation
    summary_msg = "Upstream " + ansi('boldon') + upstream_repo
    summary_msg += ansi('boldoff') + " type: " + ansi('boldon')
    summary_msg += upstream_repo_type + ansi('boldoff')
    info(summary_msg)


def validate_args(upstream_repo_type):
    # Check that the current directory is a servicable git/bloom repo
    if get_root() is None:
        error("Not in a git repository.\n")
        return False

    # Ensure that the upstream-repo-type is valid
    if upstream_repo_type not in ['git', 'svn', 'hg', 'bzr']:
        error("Invalid upstream repository type: "
              "{0}\n".format(upstream_repo_type))
        return False
    return True


@inbranch('bloom')
def show_current():
    if os.path.exists('bloom.conf'):
        info("Current bloom configuration:")
        f = open('bloom.conf', 'r')
        print('')
        map(info, [l.rstrip() for l in f.read().splitlines()])
        print('')
    else:
        info("No bloom.conf in the bloom branch")


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Configures the bloom repository with information about the upstream repository.

Example: `git-bloom-config https://github.com/ros/bloom.git git groovy-devel`
""")
    add = parser.add_argument
    add('upstream_repository', help="URI of the upstream repository",
        default='')
    add('upstream_vcs_type',
        help="type of upstream repository (git, svn, hg, or bzr)",
        default='')
    add('upstream_branch',
        help="(optional) upstream branch name from which to pull version "
             "information",
        default='', nargs="?")
    return parser


def main(sysargs=None):
    if len(sysargs if sysargs is not None else sys.argv) == 1:
        if branch_exists('bloom', False):
            show_current()
            info("See: 'git-bloom-config -h' on how to change the configs")
            return 0
        else:
            info("No bloom branch found")
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Summarize the requested operation
    summarize_arguments(args.upstream_repository, args.upstream_vcs_type,
                        args.upstream_branch)

    # Validate the arguments and repository
    if not validate_args(args.upstream_vcs_type):
        return 1

    # Store the current branch
    current_branch = get_current_branch()
    try:
        set_upstream(args.upstream_repository, args.upstream_vcs_type,
                     args.upstream_branch)
        info("Upstream successively set.")
        return 0
    finally:
        # Try to roll back to the branch the user was on before
        # this possibly failed.
        if current_branch:
            checkout(current_branch)

    return 1
