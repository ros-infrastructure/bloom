from __future__ import print_function

import sys
import traceback
import argparse

from subprocess import CalledProcessError

from bloom.branch import branch_packages

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import create_branch
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import get_root
from bloom.git import ls_tree
from bloom.git import maybe_continue
from bloom.git import track_branches

from bloom.logging import ansi
from bloom.logging import error
from bloom.logging import log_prefix
from bloom.logging import info

from bloom.patch.common import set_patch_config

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments
from bloom.util import print_exc


@log_prefix('[git-bloom-branch]: ')
def execute_branch(src, dst, interactive, directory=None):
    """
    Changes to the destination branch, creates branch and patches/branch
    if they do not exist.

    If the dst branch does not exist yet, then it is created by branching the
    current working branch or the specified SRC_BRANCH.

    If the patches/dst branch branch does not exist yet then it is created.

    If the branches are created successful, then the working branch will be
    set to the dst branch, otherwise the working branch will remain unchanged.

    :param src: source branch from which to copy
    :param dst: destination branch
    :param interactive: if True actions are summarized before committing
    :param directory: directory in which to preform this action
    :returns: return code to be passed to sys.exit

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    # Determine if the srouce branch exists
    if branch_exists(src, local_only=False, directory=directory):
        if not branch_exists(src, local_only=True, directory=directory):
            info("Tracking source branch: {0}".format(src))
            track_branches(src, directory)
    else:
        error("Specified source branch does not exist: {0}".format(src))

    # Determine if the destination branch needs to be created
    create_dst_branch = False
    if branch_exists(dst, local_only=False, directory=directory):
        if not branch_exists(dst, local_only=True, directory=directory):
            info("Tracking destination branch: {0}".format(dst))
            track_branches(dst, directory)
    else:
        create_dst_branch = True

    # Determine if the destination patches branch needs to be created
    create_dst_patches_branch = False
    dst_patches = 'patches/' + dst
    if branch_exists(dst_patches, False, directory=directory):
        if not branch_exists(dst_patches, True, directory=directory):
            track_branches(dst_patches, directory)
    else:
        create_dst_patches_branch = True

    # Summarize
    if interactive:
        info("Summary of changes:")
        if create_dst_branch:
            info("- The specified destination branch, " + ansi('boldon') + \
                 dst + ansi('reset') + ", does not exist, it will be " + \
                 "created from the source branch " + ansi('boldon') + src + \
                 ansi('reset'))
        if create_dst_patches_branch:
            info("- The destination patches branch, " + ansi('boldon') + \
                 dst_patches + ansi('reset') + " does not exist, it will be "
                 "created")
        info("- The working branch will be set to " + ansi('boldon') + dst + \
             ansi('reset'))
        if not maybe_continue():
            error("Answered no to continue, aborting.")
            return 1

    # Make changes to the layout
    current_branch = get_current_branch(directory)
    try:
        # Change to the src branch
        checkout(src, directory=directory)
        # Create the dst branch if needed
        if create_dst_branch:
            create_branch(dst, changeto=True, directory=directory)
        else:
            checkout(dst, directory=directory)
        # Create the dst patches branch if needed
        if create_dst_patches_branch:
            create_branch(dst_patches, orphaned=True, directory=directory)
        # Create the starting config data if it does not exist
        patches_ls = ls_tree(dst_patches, directory=directory)
        if 'patches.conf' not in patches_ls:
            # Patches config not setup, set it up
            config = {
                'parent': src,
                'previous': '',
                'base': get_commit_hash(dst, directory=directory),
                'trim': '',
                'trimbase': ''
            }
            set_patch_config(dst_patches, config, directory=directory)
        # Command successful, do not switch back to previous branch
        current_branch = None
    finally:
        if current_branch is not None:
            checkout(current_branch, directory=directory)
    return 0


def get_parser():
    parser = argparse.ArgumentParser(description="""\
If the DST_BRANCH does not exist yet, then it is created by branching the
current working branch or the specified SRC_BRANCH.

If the patches/DST_BRANCH branch does not exist yet then it is created.

If the branches are created successful, then the working branch will be set to
the DST_BRANCH, otherwise the working branch will remain unchanged.
""", formatter_class=argparse.RawTextHelpFormatter)
    add = parser.add_argument
    add('destination_branch', metavar="DESTINATION_BRANCH", dest='dst',
        help="destination branch name")
    add('--source-branch', '-s', metavar='SOURCE_BRANCH', dest='src',
        help="(optional) specifies which local git branch to branch from")
    add('--interactive', '-i', dest='interactive',
        help="asks before committing any changes",
        action='store_true', default=False)
    return parser


def main():
    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args()
    handle_global_arguments(args)
    retcode = 0
    try:
        # Assert this is a git repository
        if get_root() == None:
            error("Not in a valid git repository.")
            return 127
        # If the src argument isn't set, use the current branch
        if args.src is None:
            args.src = get_current_branch()
        # Execute the branching
        retcode = branch_packages(args.src, args.prefix, args.patch,
                                  args.interactive, args.continue_on_error,
                                  name=args.name)
        if retcode != 0 and not args.continue_on_error:
            print('')
            info("Stopping branching, to continue pass '--continue-on-error'")
    except CalledProcessError as err:
        # No need for a trackback here, a git call probably failed
        print_exc(traceback.format_exc())
        error(str(err))
        retcode = 1
    except Exception as err:
        # Unhandled exception, print traceback
        print_exc(traceback.format_exc())
        error(str(err))
        retcode = 2
    if retcode == 0:
        info("Working branch: " + ansi('boldon') + \
            str(get_current_branch()) + ansi('reset'))
    sys.exit(retcode)
