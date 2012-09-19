from __future__ import print_function

import sys
from argparse import ArgumentParser

from .. util import execute_command
from .. logging import error
from .. git import get_branches
from .. git import get_current_branch
from .. git import track_branches

from . common import get_patches_info


def remove_patches(directory=None):
    # Get the current branch
    current_branch = get_current_branch(directory)
    # Ensure the current branch is valid
    if current_branch is None:
        error("Could not determine current branch, are you in a git repo?")
        return 1
    # Construct the patches branch
    patches_branch = 'patches/' + current_branch
    # See if the patches branch exists
    if patches_branch in get_branches():
        # Make sure it is tracked
        if patches_branch not in get_branches(local_only=True):
            track_branches(current_branch)
    else:
        error("No patches branch (" + patches_branch + ") found, cannot "
              "remove patches.")
        return 1
    # Get the parent branch from the patches branch
    parent, spec = get_patches_info()
    if None in [parent, spec]:
        error("Could not retrieve patches configuration data.")
        return 1
    # Reset this branch using git reset --hard spec
    execute_command('git reset --hard ' + spec, cwd=directory)
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(
        description="""Removes any applied patches from the working branch."""
    )
    return parser


def main():
    return 0
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    args = parser.parse_args(sysargs)
    args  # shutup pylint
    return remove_patches()
