from __future__ import print_function

import sys
from argparse import ArgumentParser

from .. util import execute_command
from .. logging import error
from .. logging import info
from .. logging import log_prefix
from .. git import branch_exists
from .. git import get_current_branch
from .. git import has_changes

from . common import get_patch_config
from . common import list_patches


@log_prefix('[git-bloom-patch export]: ')
def export_patches(directory=None):
    # Get current branch
    current_branch = get_current_branch(directory)
    # Construct the patches branch name
    patches_branch = 'patches/' + current_branch
    # Ensure the patches branch exists
    if not branch_exists(patches_branch, False, directory=directory):
        error("The patches branch ({0}) does not ".format(patches_branch) + \
              "exist, did you use git-bloom-branch?")
        return 1
    try:
        # Get parent branch and base commit from patches branch
        config = get_patch_config(patches_branch, directory)
        if config is None:
            error("Failed to get patches information.")
            return 1
        # Checkout to the patches branch
        execute_command('git checkout ' + patches_branch, cwd=directory)
        # Notify the user
        info("Exporting patches from "
             "{0}...{1}".format(config['base'], current_branch))
        # Remove all the old patches
        if len(list_patches(directory)) > 0:
            cmd = 'git rm ./*.patch'
            execute_command(cmd, cwd=directory)
        # Create the patches using git format-patch
        cmd = "git format-patch -M -B " \
              "{0}...{1}".format(config['base'], current_branch)
        execute_command(cmd, cwd=directory)
        # Report of the number of patches created
        patches_list = list_patches(directory)
        info("Created {0} patches".format(len(patches_list)))
        # Clean up and commit
        if len(patches_list) > 0:
            cmd = 'git add ./*.patch'
            execute_command(cmd, cwd=directory)
        if has_changes(directory):
            cmd = 'git commit -m "Updating patches."'
            execute_command(cmd, cwd=directory)
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
