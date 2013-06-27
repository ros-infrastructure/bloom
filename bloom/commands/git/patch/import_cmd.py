from __future__ import print_function

import sys
import os
import tempfile
import shutil
import subprocess

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import track_branches

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import log_prefix
from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import handle_global_arguments

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import list_patches


@log_prefix('[git-bloom-patch import]: ')
def import_patches(directory=None):
    # Get current branch
    current_branch = get_current_branch(directory)
    if current_branch is None:
        error("Could not determine current branch.", exit=True)
    # Construct the patches branch name
    patches_branch = 'patches/' + current_branch
    # Ensure the patches branch exists and is tracked
    if branch_exists(patches_branch, False, directory=directory):
        if not branch_exists(patches_branch, True, directory=directory):
            track_branches(patches_branch, directory)
    else:
        error("The patches branch ({0}) does not ".format(patches_branch) +
              "exist, did you use git-bloom-branch?", exit=True)
    # Create a swap space
    tmp_dir = tempfile.mkdtemp()
    try:
        # Get parent branch and base commit from patches branch
        config = get_patch_config(patches_branch, directory)
        parent_branch, commit = config['parent'], config['base']
        if commit != get_commit_hash(current_branch, directory):
            debug(
                "commit != get_commit_hash(current_branch, directory)"
            )
            debug(
                "{0} != get_commit_hash({1}, {2}) != {3}".format(
                    commit, current_branch, directory,
                    get_commit_hash(current_branch, directory)
                )
            )
            os.system('git log')
            warning(
                "The current commit is not the same as the most recent "
                "rebase commit."
            )
            warning(
                "This might mean that you have committed since the last "
                "time you did:"
            )
            warning(
                "    'git-bloom-patch rebase' or 'git-bloom-patch remove'"
            )
            warning(
                "Make sure you export any commits you want to save first:"
            )
            warning("    'git-bloom-patch export'")
            error("Patches not exported", exit=True)
        # Checkout to the patches branch
        checkout(patches_branch, directory=directory)
        # Copy the patches to a temp location
        patches = list_patches(directory)
        if len(patches) == 0:
            debug("No patches in the patches branch, nothing to do")
            return -1  # Indicates that nothing was done
        tmp_dir_patches = []
        for patch in patches:
            tmp_dir_patches.append(os.path.join(tmp_dir, patch))
            if directory is not None:
                patch = os.path.join(directory, patch)
            shutil.copy(patch, tmp_dir)
        # Now checkout back to the original branch and import them
        checkout(current_branch, directory=directory)
        try:
            cmd = 'git am {0}*.patch'.format(tmp_dir + os.sep)
            execute_command(cmd, cwd=directory)
        except subprocess.CalledProcessError as e:
            warning("Failed to apply one or more patches for the "
                    "'{0}' branch.".format(str(e)))
            info('', use_prefix=False)
            info('', use_prefix=False)
            info(">>> Resolve any conflicts and when you have resolved this "
                 "problem run 'git am --resolved' and then exit the "
                 "shell using 'exit 0'. <<<", use_prefix=False)
            info("    To abort use 'exit 1'", use_prefix=False)
            if 'bash' in os.environ['SHELL']:
                ret = subprocess.call([
                    "/bin/bash", "-l", "-c",
                    """\
/bin/bash --rcfile <(echo "if [ -f /etc/bashrc ]; then source /etc/bashrc; fi; \
if [ -f ~/.bashrc ]; then source ~/.bashrc; fi;PS1='(bloom)$PS1'") -i"""
                ])
            else:
                ret = subprocess.call("$SHELL", shell=True)
            if ret != 0:
                error("User failed to resolve patch conflicts, exiting.")
                sys.exit("'git-bloom-patch import' aborted.")
            info("User reports that conflicts have been resolved, continuing.")
        # Notify the user
        info("Applied {0} patches".format(len(patches)))
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'import',
        description="""\
Imports the patches from the patches branch, which is named
'patches/<current branch name>', onto the current working branch.
"""
    )
    parser.set_defaults(func=main)
    add_global_arguments(parser)
    return parser


def main(args):
    handle_global_arguments(args)
    return import_patches()
