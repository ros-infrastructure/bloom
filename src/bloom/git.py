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

"""Advanced utilities for manipulating git repositories"""

from __future__ import print_function

from subprocess import PIPE, CalledProcessError

from bloom.util import execute_command
from bloom.util import check_output


def get_root(directory=None):
    """
    Returns the git root directory above the given dir.

    If the given dir is not in a git repository, None is returned.

    :param directory: directory to query from, if None the cwd is used
    :returns: root of git repository or None if not a git repository
    """
    cmd = 'git rev-parse --show-toplevel'
    try:
        output = check_output(cmd, shell=True, cwd=directory)
    except CalledProcessError:
        return None
    return output


def get_current_branch(directory=None):
    """
    Returns the current git branch by parsing the output of `git branch`

    This will raise a RuntimeError if the current working directory is not
    a git repository.  If no branch could be determined it will return None,
    i.e. (no branch) will return None.

    :param directory: directory in which to run the command
    :returns: current git branch or None if none can be determined, (no branch)
    """
    cmd = 'git branch --no-color'
    output = check_output(cmd, shell=True, cwd=directory)
    output = output.splitlines()
    for token in output:
        if token.strip().startswith('*'):
            token = token[2:]
            if token == '(no branch)':
                return None
            return token
    return None


def track_branches(branches=None, cwd=None):
    """
    Tracks all specified branches.

    :param branches: a list of branches that are to be tracked if not already
    tracked.  If this is set to None then all remote branches will be tracked.
    """
    # TODO: replace listing of branches with vcstool's get_branches
    # Save current branch
    current_branch = get_current_branch(cwd)
    # Get the local branches
    local_branches = check_output('git branch', shell=True, cwd=cwd)
    local_branches = local_branches.splitlines()
    # Strip local_branches of white space
    for index, local_branch in enumerate(local_branches):
        local_branches[index] = local_branch.strip('*').strip()
    # Either get the remotes or use the given list of branches to track
    remotes_out = check_output('git branch -r', shell=True, cwd=cwd)
    remotes = remotes_out.splitlines()
    if branches == None:
        branches = remotes
    # Subtract the locals from the remotes
    to_track = []
    for remote in branches:
        remote = remote.strip()
        if remote.count('master') != 0:
            continue
        if remote.count('/') > 0:
            remote_branch = remote.split('/')[1]
        else:
            remote_branch = remote
        if remote_branch not in local_branches:
            to_track.append(remote_branch)
    # Now track any remotes that are not local
    for branch in to_track:
        if remotes_out.count(branch) > 0:
            cmd = 'git checkout --track -b {0}'.format(branch)
            execute_command(cmd, cwd=cwd)
    # Restore original branch
    if current_branch:
        execute_command('git checkout {0}'.format(current_branch), cwd=cwd)


def get_last_tag_by_date(cwd=None):
    """
    Returns the most recent, by date, tag in the given local git repository.

    :param cwd: the directory in which to run the query
    :returns: the most recent tag by date, else '' if there are no tags
    """
    cmd = "git for-each-ref --sort='*authordate' " \
          "--format='%(refname:short)' refs/tags/upstream"
    output = check_output(cmd, shell=True, cwd=cwd, stderr=PIPE)
    output = output.splitlines()
    if len(output) == 0:
        return ''
    return output[-1]
