from __future__ import print_function

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import ensure_clean_working_env
from bloom.git import ensure_git_root
from bloom.git import get_current_branch
from bloom.git import has_changes

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import log_prefix

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import handle_global_arguments

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import list_patches


@log_prefix('[git-bloom-patch export]: ')
def export_patches(directory=None):
    # Ensure a clean/valid working environment
    ensure_clean_working_env(git_status=True, directory=directory)
    # Get current branch
    current_branch = get_current_branch(directory)
    if current_branch is None:
        error("Could not determine current branch.", exit=True)
    # Construct the patches branch name
    patches_branch = 'patches/' + current_branch
    # Ensure the patches branch exists
    if not branch_exists(patches_branch, False, directory=directory):
        error("The patches branch ({0}) does not ".format(patches_branch) +
              "exist, did you use git-bloom-branch?", exit=True)
    try:
        # Get parent branch and base commit from patches branch
        config = get_patch_config(patches_branch, directory)
        if config is None:
            error("Failed to get patches information.", exit=True)
        # Checkout to the patches branch
        checkout(patches_branch, directory=directory)
        # Notify the user
        debug("Exporting patches from "
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
        debug("Created {0} patches".format(len(patches_list)))
        # Clean up and commit
        if len(patches_list) > 0:
            cmd = 'git add ./*.patch'
            execute_command(cmd, cwd=directory)
        if has_changes(directory):
            cmd = 'git commit -m "Updating patches."'
            execute_command(cmd, cwd=directory)
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)


def add_parser(subparsers):
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = subparsers.add_parser(
        'export',
        description="""\
Exports the commits that have been made on the current branch since the
original source branch (source branch from git-bloom-branch) to a patches
branch, which is named 'patches/<current branch name>', using git format-patch.
"""
    )
    parser.set_defaults(func=main)
    add_global_arguments(parser)
    return parser


def main(args):
    handle_global_arguments(args)

    ensure_git_root()

    return export_patches()
