from __future__ import print_function

import sys
import traceback
from argparse import ArgumentParser

from .. util import add_global_arguments
from .. util import execute_command
from .. util import handle_global_arguments
from .. logging import error
from .. logging import log_prefix
from .. logging import warning
from .. git import get_commit_hash
from .. git import get_current_branch

from . remove_cmd import remove_patches
from . import_cmd import import_patches
from . trim_cmd import trim
from . common import get_patch_config
from . common import set_patch_config
from . common import update_tag


@log_prefix('[git-bloom-patch rebase]: ')
def rebase_patches(directory=None):
    # Make sure we need to actually call this
    current_branch = get_current_branch(directory)
    patches_branch = 'patches/' + current_branch
    config = get_patch_config(patches_branch, directory=directory)
    upstream_commit_hash = get_commit_hash(config['parent'], directory)
    current_commit_hash = get_commit_hash(current_branch, directory)
    if current_commit_hash == upstream_commit_hash:
        warning("""\
The base commit of this branch is the same as its parent's current commit. \
This command would have no effect, did you forget to update the parent branch \
first? Updating the parent branch can be done by calling 'git-bloom-patch \
rebase' on it, or 'git-bloom-import-upsteam' if the parent branch is the \
upstream branch.\
""")
        return 1
    # Call git-bloom-patch remove
    try:
        remove_patches(directory)
    except Exception as err:
        traceback.print_exc()
        error(str(err))
        return 2
    # Remove the trim
    try:
        if config['trimbase'] != '':
            trim(undo=True, directory=directory)
    except Exception as err:
        traceback.print_exc()
        error(str(err))
        return 3
    # Attempt to merge in the upstream changes
    execute_command('git merge -Xtheirs ' + config['parent'], cwd=directory)
    config = get_patch_config(patches_branch, directory)
    config['base'] = get_commit_hash(current_branch, directory)
    set_patch_config(patches_branch, config, directory)
    # Reapply the trimming
    try:
        if config['trim'] != '':
            trim(directory=directory)
    except Exception as err:
        traceback.print_exc()
        error(str(err))
        return 4
    # Reapply the patches
    try:
        import_patches(directory)
    except Exception as err:
        traceback.print_exc()
        error(str(err))
        return 5
    # Update the tag
    update_tag()
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(
        description="""Removes any applied patches from the working branch,
attempts to merge changes from the parent branch, and then attempts to reapply
the patches."""
    )
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    return rebase_patches()
