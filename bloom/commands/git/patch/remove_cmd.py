from __future__ import print_function

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import track_branches

from bloom.logging import log_prefix
from bloom.logging import error
from bloom.logging import debug

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import handle_global_arguments


@log_prefix('[git-bloom-patch remove]: ')
def remove_patches(directory=None):
    # Get the current branch
    current_branch = get_current_branch(directory)
    if current_branch is None:
        error("Could not determine current branch.", exit=True)
    # Ensure the current branch is valid
    if current_branch is None:
        error("Could not determine current branch, are you in a git repo?",
              exit=True)
    # Construct the patches branch
    patches_branch = 'patches/' + current_branch
    try:
        # See if the patches branch exists
        if branch_exists(patches_branch, False, directory=directory):
            if not branch_exists(patches_branch, True, directory=directory):
                track_branches(patches_branch, directory)
        else:
            error("No patches branch (" + patches_branch + ") found, cannot "
                  "remove patches.", exit=True)
        # Get the parent branch from the patches branch
        config = get_patch_config(patches_branch, directory=directory)
        parent, spec = config['parent'], config['base']
        if None in [parent, spec]:
            error("Could not retrieve patches info.", exit=True)
        debug("Removing patches from " + current_branch + " back to base "
              "commit " + spec)
        # Reset this branch using git revert --no-edit spec
        current_commit = get_commit_hash(current_branch, directory)
        command_spec = spec + '..' + current_commit
        execute_command(
            'git revert --no-edit -Xtheirs ' + command_spec, cwd=directory
        )
        # Update the base
        config['base'] = get_commit_hash(current_branch, directory)
        set_patch_config(patches_branch, config, directory=directory)
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'remove',
        description="Removes any applied patches from the working branch, "
                    "including any un-exported patches, so use with caution."
    )
    parser.set_defaults(func=main)
    add_global_arguments(parser)
    return parser


def main(args):
    handle_global_arguments(args)
    return remove_patches()
