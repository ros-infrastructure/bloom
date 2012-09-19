from __future__ import print_function

import sys
from argparse import ArgumentParser

from .. util import execute_command
from .. logging import error
from .. logging import info
from .. git import get_branches
from .. git import get_current_branch

from . common import get_patches_info
from . common import list_patches


def export_patches(directory=None):
    # Get current branch
    current_branch = get_current_branch(directory)
    # Construct the patches branch name
    patches_branch = 'patches/' + current_branch
    # Ensure the patches branch exists
    if patches_branch not in get_branches():
        error("The patches branch ({0}) does not ".format(patches_branch) + \
              "exist, did you use git-bloom-branch?")
        return 1
    try:
        # Get parent branch and base commit from patches branch
        parent_branch, _ = get_patches_info(patches_branch, directory)
        # Checkout to the patches branch
        execute_command('git checkout ' + patches_branch, cwd=directory)
        # Notify the user
        info("Exporting patches from "
             "{0}...{1}".format(parent_branch, current_branch))
        # Create the patches using git format-patch
        cmd = "git format-patch -M -B " \
              "{0}...{1}".format(parent_branch, current_branch)
        execute_command(cmd, cwd=directory)
        # Report of the number of patches created
        patches_list = list_patches(directory)
        info("Created {0} patches".format(len(patches_list)))
    finally:
        if current_branch:
            execute_command('git checkout ' + current_branch, cwd=directory)
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(
        description="""\
Exports the commits that have been made on the current branch since the
original parent branch (source branch from git-bloom-branch) to a patches
branch, which is named 'patches/<current branch name>', using git format-patch.
"""
    )
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    args = parser.parse_args(sysargs)
    args  # pylint
    return export_patches()
