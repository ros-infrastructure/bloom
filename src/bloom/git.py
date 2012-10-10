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

import os

from subprocess import PIPE, CalledProcessError

from . logging import debug
from . logging import error
from . logging import warning
import functools

from . util import execute_command
from . util import check_output
from . util import pdb_hook


def ls_tree(reference, path=None, directory=None):
    """
    Returns a dictionary of files and folders for a given reference and path.

    Implemented using ``git ls-tree``. If an invalid reference and/or path
    None is returned.

    :param reference: git reference to pull from (branch, tag, or commit)
    :param path: tree to list
    :param directory: directory in which to run this command

    :returns: dict if a directory (or a reference) or None if it does not exist

    :raises: subprocess.CalledProcessError if any git calls fail
    :raises: RuntimeError if the output from git is not what we expected
    """
    # Try to track the reference as a branch
    track_branches(reference, directory=directory)
    cmd = 'git ls-tree ' + reference
    if path is not None and path != '':
        cmd += ':' + path
    retcode, out, err = execute_command(cmd, autofail=False, silent_error=True,
                                        cwd=directory, return_io=True)
    if retcode != 0:
        return None
    items = {}
    for line in out.splitlines():
        tokens = line.split()
        if len(tokens) != 4:
            return None
        if tokens[1] not in ['blob', 'tree']:
            raise RuntimeError("item not a blob or tree")
        if tokens[3] in items:
            raise RuntimeError("duplicate name in ls tree")
        items[tokens[3]] = 'file' if tokens[1] == 'blob' else 'directory'
    return items


def show(reference, path, directory=None):
    """
    Interface to the git show command.

    If path is a file that exists, a string will be returned which is the
    contents of that file. If the path is a directory that exists, then a
    dictionary is returned where the keys are items in the folder and the
    value is either the string 'file' or 'directory'. If the path does not
    exist then this returns None.

    :param reference: git reference to pull from (branch, tag, or commit)
    :param path: path to show or list
    :param directory: directory in which to run this command

    :returns: string if a file, dict if a directory, None if it does not exist

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    # Check to see if this is a directory
    dirs = ls_tree(reference, path, directory)
    if dirs is not None:
        return dirs
    # Otherwise a file or does not exist, check for the file
    cmd = 'git show {0}:{1}'.format(reference, path)
    # Check to see if it is a directory
    retcode, out, err = execute_command(cmd, autofail=False, silent_error=True,
                                        cwd=directory, return_io=True)
    if retcode != 0:
        # Does not exist
        return None
    # It is a file that exists, return the output
    return out


def ensure_clean_working_env(force=False, git_status=True, directory=None):
    """
    Returns 0 if the working environment is clean, otherwise 1.

    Clean is defined as:
        - In a git repository
        - In a valid branch (force overrides)
        - Does not have local changes (force overrides)
        - Does not have untracked files (force overrides)

    :param force: If True, overrides a few of the fail conditions
    :param directory: directory in which to run this command

    :returns: 0 if the env is clean, otherwise 1

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    def ecwe_fail(show_git_status):
        if show_git_status:
            print('\n++ git status:\n')
            os.system('git status')
        return 1
    # Is it a git repo
    if get_root(directory) is None:
        error("Not is a valid git repository")
        return 1
    # Are we on a branch?
    current_branch = get_current_branch(directory)
    if current_branch is None:
        msg = warning if force else error
        msg("Could not determine current branch")
        if not force:
            return ecwe_fail(git_status)
    # Are there local changes?
    if has_changes(directory):
        msg = warning if force else error
        msg("Current git working branch has local changes")
        if not force:
            return ecwe_fail(git_status)
    # Are there untracked files or directories?
    if has_untracked_files(directory):
        msg = warning if force else error
        msg("Current git working branch has untracked files/directories")
        if not force:
            return ecwe_fail(git_status)
    return 0


def checkout(reference, raise_exc=False, directory=None):
    """
    Returns True if the checkout to a the reference was successful, else False

    :param reference: branch, tag, or commit hash to checkout to
    :param directory: directory in which to run this command

    :returns: True if the checkout was successful, else False
    """
    def checkout_summarize(fail_msg, branch, directory):
        branch = '(no branch)' if branch is None else branch
        directory = os.getcwd() if directory is None else directory
        error("Failed to checkout to '{0}'".format(str(reference)) + \
              " because the working directory {0}".format(str(fail_msg)))
        debug("  Working directory:   '{0}'".format(str(directory)))
        debug("  Working branch:      '{0}'".format(str(branch)))
        debug("  Has local changes:   '{0}'".format(str(changes)))
        debug("  Has untrakced files: '{0}'".format(str(untracked)))
        pdb_hook()
        return 1
    debug("Checking out to " + str(reference))
    if reference == get_current_branch(directory):
        debug("Requested checkout reference is the same as the current branch")
        return 0
    fail_msg = ''
    git_root = get_root(directory)
    if git_root is not None:
        changes = has_changes(directory)
        untracked = has_untracked_files(directory)
        branch = get_current_branch(directory)
    else:
        fail_msg = "is not a git repository"
    if fail_msg == '' and changes:
        fail_msg = "has local changes"
    if fail_msg == '' and untracked:
        fail_msg = "has untracked files"
    try:
        if not changes and not untracked:
            execute_command('git checkout "{0}"'.format(str(reference)),
                            cwd=directory)

    except CalledProcessError as err:
        fail_msg = "CalledProcessError: " + str(err)
        if raise_exc:
            checkout_summarize(fail_msg)
            raise
    if fail_msg != '':
        return checkout_summarize(fail_msg, branch, directory)
    else:
        return 0


def branch_exists(branch_name, local_only=False, directory=None):
    """
    Returns true if a given branch exists locally or remotelly

    :param branch_name: name of the branch to look for
    :param local_only: if True, only look at the local branches
    :param directory: directory in which to run this command

    :returns: True if the branch is in the list of branches from git

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    for branch in get_branches(local_only, directory):
        if branch.startswith('remotes/'):
            branch = branch.split('/')
            if len(branch) > 2:
                branch = '/'.join(branch[2:])
                if branch_name == branch:
                    return True
        else:
            if branch_name == branch:
                return True
    return False


class ContextDecorator(object):
    def __call__(self, f):
        @functools.wraps(f)
        def decorated(*args, **kwds):
            with self:
                return f(*args, **kwds)
        return decorated


class inbranch(ContextDecorator):
    """
    Safely switches to a given branch on entry and switches back on exit.

    Combination decorator/context manager, therefore it can be used like:

        @inbranch('some_git_branch')
        def foo():
            pass

    Or in conjunction with the 'with' statement:

        with inbranch('some_git_branch'):
            foo()

    :param branch_name: name of the branch to switch to
    :param directory: directory in which to run the branch change

    :raises: subprocess.CalledProcessError if either 'git checkout' call fails
    """
    def __init__(self, branch, directory=None):
        self.branch = branch
        self.directory = directory

    def __enter__(self):
        self.current_branch = get_current_branch(self.directory)
        checkout(self.branch, raise_exc=True, directory=self.directory)

    def __exit__(self, exc_type, exc_value, traceback):
        checkout(self.current_branch, raise_exc=True, directory=self.directory)


def get_commit_hash(reference, directory=None):
    """
    Returns the SHA-1 commit hash for the given reference.

    :param reference: any git reference (branch or tag) to resolve to SHA-1
    :param directory: directory in which to preform this action
    :returns: SHA-1 commit hash for the given reference

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    # Track remote branch
    if branch_exists(reference, local_only=False, directory=directory):
        if not branch_exists(reference, local_only=True, directory=directory):
            track_branches(reference, directory)
    cmd = 'git show-branch --sha1-name ' + reference
    out = check_output(cmd, shell=True, cwd=directory)
    return out.split('[')[1].split(']')[0]


def has_untracked_files(directory=None):
    """
    Returns True is the working branch has untracked files, False otherwise.

    :param directory: directory in which to preform this action
    :returns: True if there are untracked files (or dirs), otherwise False

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    out = check_output('git status', shell=True, cwd=directory)
    if '# Untracked files:' in out:
        return True
    return False


def has_changes(directory=None):
    """
    Returns True if the working branch has local changes, False otherwise.

    :param directory: directory in which to preform this action
    :returns: True if there are local changes, otherwise False

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    out = check_output('git status', shell=True, cwd=directory)
    if 'nothing to commit (working directory clean)' in out:
        return False
    if 'nothing added to commit' in out:
        return False
    return True


def get_branches(local_only=False, directory=None):
    """
    Returns a list of branches in the git repository.

    :param local_only: if True, do not return remote branches, False by default
    :param directory: directory in which to preform this action
    :returns: list of branches

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    cmd = 'git branch --no-color'
    if not local_only:
        cmd += ' -a'
    out = check_output(cmd, shell=True, cwd=directory)
    branches = []
    for line in out.splitlines():
        if line.count('HEAD -> ') > 0:
            continue
        if line.count('(no branch)') > 0:
            continue
        line = line.strip('*').strip()
        branches.append(line)
    return branches


def create_branch(branch, orphaned=False, changeto=False, directory=None):
    """
    Creates a new branch in the current, or given, git repository.

    If the specified branch already exists git will fail and a
    subprocess.CalledProcessError will be raised.

    :param branch: name of the new branch
    :param orphaned: if True creates an orphaned branch
    :param changeto: if True changes to the new branch after creation
    :param directory: directory in which to preform this action

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    current_branch = get_current_branch(directory)
    try:
        if orphaned:
            execute_command('git symbolic-ref HEAD refs/heads/' + branch,
                            cwd=directory)
            execute_command('rm -f .git/index', cwd=directory)
            execute_command('git clean -fdx', cwd=directory)
            cmd = 'git commit --allow-empty -m "Created orphaned branch '\
                  '{0}"'.format(branch)
            execute_command(cmd, cwd=directory)
            if changeto:
                current_branch = None
        else:
            execute_command('git branch {0}'.format(branch), cwd=directory)
            if changeto:
                checkout(branch, directory=directory)
            current_branch = None
    finally:
        if current_branch is not None:
            checkout(current_branch, directory=directory)


def get_root(directory=None):
    """
    Returns the git root directory above the given dir.

    If the given dir is not in a git repository, None is returned.

    :param directory: directory to query from, if None the cwd is used
    :returns: root of git repository or None if not a git repository
    """
    cmd = 'git rev-parse --show-toplevel'
    try:
        output = check_output(cmd, shell=True, cwd=directory, stderr=PIPE)
    except CalledProcessError:
        return None
    return output.strip()


def get_current_branch(directory=None):
    """
    Returns the current git branch by parsing the output of `git branch`

    This will raise a RuntimeError if the current working directory is not
    a git repository.  If no branch could be determined it will return None,
    i.e. (no branch) will return None.

    :param directory: directory in which to run the command
    :returns: current git branch or None if none can be determined, (no branch)

    :raises: subprocess.CalledProcessError if git command fails
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


def track_branches(branches=None, directory=None):
    """
    Tracks all specified branches.

    :param branches: a list of branches that are to be tracked if not already
    tracked.  If this is set to None then all remote branches will be tracked.
    :param directory: directory in which to run all commands

    :raises: subprocess.CalledProcessError if git command fails
    """
    if type(branches) == str:
        branches = [branches]
    debug("track_branches(" + str(branches) + ", " + str(directory) + ")")
    if branches == []:
        return
    # Save the current branch
    current_branch = get_current_branch(directory)
    try:
        # Get the local branches
        local_branches = get_branches(local_only=True, directory=directory)
        # Get the remote and local branches
        all_branches = get_branches(local_only=False, directory=directory)
        # Calculate the untracked branches
        untracked_branches = []
        for branch in all_branches:
            if branch.startswith('remotes/'):
                if branch.count('/') >= 2:
                    branch = '/'.join(branch.split('/')[2:])
            if branch not in local_branches:
                untracked_branches.append(branch)
        # Prune any untracked branches by specified branches
        if branches is not None:
            branches_to_track = []
            for untracked in untracked_branches:
                if untracked in branches:
                    branches_to_track.append(untracked)
        else:
            branches_to_track = untracked_branches
        # Track branches
        debug("Tracking branches: " + str(branches_to_track))
        for branch in branches_to_track:
            checkout(branch, directory=directory)
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)


def get_last_tag_by_date(directory=None):
    """
    Returns the most recent, by date, tag in the given local git repository.

    :param directory: the directory in which to run the query
    :returns: the most recent tag by date, else '' if there are no tags

    :raises: subprocess.CalledProcessError if git command fails
    """
    cmd = "git for-each-ref --sort='*authordate' " \
          "--format='%(refname:short)' refs/tags/upstream"
    output = check_output(cmd, shell=True, cwd=directory, stderr=PIPE)
    output = output.splitlines()
    if len(output) == 0:
        return ''
    return output[-1]
