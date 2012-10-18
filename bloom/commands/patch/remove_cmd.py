from __future__ import print_function

import sys
from argparse import ArgumentParser

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import handle_global_arguments
from bloom.logging import log_prefix
from bloom.logging import error
from bloom.logging import debug
from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import get_current_branch
from bloom.git import track_branches

from bloom.commands.patch.common import get_patch_config


@log_prefix('[git-bloom-patch remove]: ')
def remove_patches(directory=None):
    # Get the current branch
    current_branch = get_current_branch(directory)
    # Ensure the current branch is valid
    if current_branch is None:
        error("Could not determine current branch, are you in a git repo?")
        return 1
    # Construct the patches branch
    patches_branch = 'patches/' + current_branch
    try:
        # See if the patches branch exists
        if branch_exists(patches_branch, False, directory=directory):
            if not branch_exists(patches_branch, True, directory=directory):
                track_branches(patches_branch, directory)
        else:
            error("No patches branch (" + patches_branch + ") found, cannot "
                  "remove patches.")
            return 1
        # Get the parent branch from the patches branch
        config = get_patch_config(patches_branch, directory=directory)
        parent, spec = config['parent'], config['base']
        if None in [parent, spec]:
            error("Could not retrieve patches info.")
            return 1
        debug("Removing patches from " + current_branch + " back to base "
              "commit " + spec)
        # Reset this branch using git reset --hard spec
        execute_command('git reset --hard ' + spec, cwd=directory)
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(description="""
Removes any applied patches from the working branch, including any un-exported
patches, so use with caution.
""")
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    return remove_patches()
