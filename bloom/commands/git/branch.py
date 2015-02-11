from __future__ import print_function

import argparse

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import create_branch
from bloom.git import ensure_clean_working_env
from bloom.git import ensure_git_root
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import ls_tree
from bloom.git import tag_exists
from bloom.git import track_branches

from bloom.logging import ansi
from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import log_prefix
from bloom.logging import warning

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments
from bloom.util import maybe_continue


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

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    # Determine if the srouce branch exists
    if src is None:
        error("No source specified and/or not a branch currently", exit=True)
    if branch_exists(src, local_only=False, directory=directory):
        if not branch_exists(src, local_only=True, directory=directory):
            debug("Tracking source branch: {0}".format(src))
            track_branches(src, directory)
    elif tag_exists(src):
        pass
    else:
        error("Specified source branch does not exist: {0}".format(src),
              exit=True)

    # Determine if the destination branch needs to be created
    create_dst_branch = False
    if branch_exists(dst, local_only=False, directory=directory):
        if not branch_exists(dst, local_only=True, directory=directory):
            debug("Tracking destination branch: {0}".format(dst))
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
            info(" " * 22 + "- The specified destination branch, " +
                 ansi('boldon') + dst + ansi('reset') +
                 ", does not exist; it will be created from the source "
                 "branch " + ansi('boldon') + src + ansi('reset'))
        if create_dst_patches_branch:
            info(" " * 22 + "- The destination patches branch, " +
                 ansi('boldon') + dst_patches + ansi('reset') +
                 ", does not exist; it will be created")
        info(" " * 22 + "- The working branch will be set to " +
             ansi('boldon') + dst + ansi('reset'))
        if not maybe_continue():
            error("Answered no to continue, aborting.", exit=True)

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
        else:
            config = get_patch_config(dst_patches, directory=directory)
            if config['parent'] != src:
                warning("Updated parent to '{0}' from '{1}'"
                        .format(src, config['parent']))
                config['parent'] = src
                config['base'] = get_commit_hash(dst, directory=directory)
            set_patch_config(dst_patches, config, directory=directory)
        # Command successful, do not switch back to previous branch
        current_branch = None
    finally:
        if current_branch is not None:
            checkout(current_branch, directory=directory)


def get_parser():
    parser = argparse.ArgumentParser(description="""\
If the DESTINATION_BRANCH does not exist yet, then it is created by
branching the current working branch or the specified SOURCE_BRANCH.

If the patches/DESTINATION_BRANCH branch does not exist yet then it is created.

If the branches are created successful, then the working branch will be set to
the DESTINATION_BRANCH, otherwise the working branch will remain unchanged.
""", formatter_class=argparse.RawTextHelpFormatter)
    add = parser.add_argument
    add('destination_branch', metavar='DESTINATION_BRANCH',
        help="destination branch name")
    add('-s', '--src', '--source-branch', metavar='SOURCE_BRANCH', dest='src',
        help="(optional) specifies which local git branch to branch from")
    add('-i', '--interactive', dest='interactive',
        help="asks before committing any changes",
        action='store_true', default=False)
    return parser


def main(sysargs=None):
    from bloom.config import upconvert_bloom_to_config_branch
    upconvert_bloom_to_config_branch()

    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Check that the current directory is a serviceable git/bloom repo
    try:
        ensure_clean_working_env()
        ensure_git_root()
    except SystemExit:
        parser.print_usage()
        raise

    # If the src argument isn't set, use the current branch
    if args.src is None:
        args.src = get_current_branch()
    # Execute the branching
    execute_branch(args.src, args.destination_branch, args.interactive)
