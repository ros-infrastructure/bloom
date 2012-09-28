from __future__ import print_function

import sys
import os
import tempfile
import shutil
from argparse import ArgumentParser

from .. util import add_global_arguments
from .. util import execute_command
from .. util import handle_global_arguments
from .. logging import error
from .. logging import info
from .. logging import log_prefix
from .. logging import warning
from .. git import branch_exists
from .. git import checkout
from .. git import get_commit_hash
from .. git import get_current_branch
from .. git import track_branches

from . common import get_patch_config
from . common import list_patches
from . common import update_tag


@log_prefix('[git-bloom-patch import]: ')
def import_patches(directory=None):
    # Get current branch
    current_branch = get_current_branch(directory)
    # Construct the patches branch name
    patches_branch = 'patches/' + current_branch
    # Ensure the patches branch exists and is tracked
    if branch_exists(patches_branch, False, directory=directory):
        if not branch_exists(patches_branch, True, directory=directory):
            track_branches(patches_branch, directory)
    else:
        error("The patches branch ({0}) does not ".format(patches_branch) + \
              "exist, did you use git-bloom-branch?")
        return 1
    # Create a swap space
    tmp_dir = tempfile.mkdtemp()
    try:
        # Get parent branch and base commit from patches branch
        config = get_patch_config(patches_branch, directory)
        parent_branch, commit = config['parent'], config['base']
        if commit != get_commit_hash(current_branch, directory):
            warning("The current commit is not the same as the most recent "
                    "rebase commit. This might mean that you have committed "
                    "since the last time you did 'git-bloom-patch export'.")
            return 1
        # Checkout to the patches branch
        checkout(patches_branch, directory=directory)
        # Copy the patches to a temp location
        patches = list_patches(directory)
        if len(patches) == 0:
            warning("No patches in the patches branch, nothing to do")
            return 1
        tmp_dir_patches = []
        for patch in patches:
            tmp_dir_patches.append(os.path.join(tmp_dir, patch))
            if directory is not None:
                patch = os.path.join(directory, patch)
            shutil.copy(patch, tmp_dir)
        # Now checkout back to the original branch and import them
        checkout(current_branch, directory=directory)
        cmd = 'git am {0}*.patch'.format(tmp_dir + os.sep)
        execute_command(cmd, cwd=directory)
        # Notify the user
        info("Applied {0} patches".format(len(patches)))
        # Update the tag
        update_tag()
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(
        description="""\
Imports the patches from the patches branch, which is named
'patches/<current branch name>', onto the current working branch.
"""
    )
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    return import_patches()
