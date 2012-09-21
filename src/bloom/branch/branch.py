from __future__ import print_function

from .. util import execute_command
from .. util import maybe_continue
from .. logging import ansi
from .. logging import error
from .. logging import info
from .. logging import warning
from .. git import create_branch
from .. git import get_branches
from .. git import get_commit_hash
from .. git import get_current_branch
from .. git import track_branches

from .. patch.common import set_patch_config
from .. patch.common import get_patch_config
from .. patch.rebase_cmd import rebase_patches
from .. patch.trim_cmd import trim

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr)
    sys.exit(1)



def execute_branch(src, dst, patch, interactive, trim_dir='', directory=None):
    """
    executes bloom branch from src to dst and optionally will patch

    If the dst branch does not exist yet, then it is created by branching the
    current working branch or the specified SRC_BRANCH.

    If the patches/dst branch branch does not exist yet then it is created.

    If the branches are created successful, then the working branch will be
    set to the dst branch, otherwise the working branch will remain unchanged.

    If the dst branch and patches/dst branch already existed, then a call to
    `git-bloom-patch rebase` is attempted unless patch is False.

    :param src: source branch from which to copy
    :param dst: destination branch to copy to
    :param patch: whether or not to apply previous patches to destination
    :param interactive: if True actions are summarized before committing
    :param trim_dir: sub directory to move to the root of git dst branch
    :param directory: directory in which to preform this action
    :returns: return code to be passed to sys.exit

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    branches = get_branches(directory)
    local_branches = get_branches(local_only=True, directory=directory)
    if src in branches:
        if src not in local_branches:
            track_branches(src, directory)
    else:
        error("Specified source branch does not exist: {0}".format(src))

    create_dst_branch = False
    if dst in branches:
        if dst not in local_branches:
            track_branches(dst, directory)
    else:
        create_dst_branch = True

    create_dst_patches_branch = False
    dst_patches = 'patches/' + dst
    if dst_patches in branches:
        if dst_patches not in local_branches:
            track_branches(dst_patches, directory)
    else:
        create_dst_patches_branch = True

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

    current_branch = get_current_branch(directory)
    try:
        # Change to the src branch
        execute_command('git checkout {0}'.format(src), cwd=directory)
        # Create the dst branch if needed
        if create_dst_branch:
            create_branch(dst, changeto=True, directory=directory)
        else:
            execute_command('git checkout {0}'.format(dst), cwd=directory)
        config = None
        # Create the dst patches branch if needed
        if create_dst_patches_branch:
            create_branch(dst_patches, orphaned=True, directory=directory)
        else:
            # Get the patches info and compare it, warn of changing parent
            config = get_patch_config(dst_patches, directory)
            if config is None:
                error("Failed to retreive patch config from " + dst_patches)
                return 1
            if config['parent'] != src:
                warning("You are changing the parent branch to " + src + \
                        " from " + config['parent'] + ", are you sure you "
                        "want to do this?")
                if not maybe_continue():
                    error("Answered no to continue, aborting.")
                    return 1
            if trim_dir != '' and config['trim'] != trim_dir:
                warning("You are changing the sub directory for the "
                        "destination branch to " + trim_dir + " from " + \
                        config['trim'] + ", are you sure you want to do this?")
                if not maybe_continue():
                    error("Answered no to continue, aborting.")
                    return 1
        # Get the current commit hash as a baseline
        commit_hash = get_commit_hash(dst, directory=directory)
        # Set the patch config
        config = {'parent': src,
                  'base': commit_hash,
                  'trim': config['trim'] if config is not None else '',
                  'trimbase': config['trimbase'] if config is not None else ''}
        set_patch_config(dst_patches, config, directory=directory)
        # Command is successful, even if applying patches fails
        current_branch = None
        execute_command('git checkout ' + dst, cwd=directory)
        # If trim_dir is set, trim the resulting directory
        if trim_dir not in ['', '.']:
            trim(trim_dir, False, False, directory)
        # Try to update if appropriate
        if not create_dst_branch and not create_dst_patches_branch:
            if patch:
                # Execute git-bloom-patch rebase
                rebase_patches(directory=directory)
            else:
                info("Skipping call to 'git-bloom-patch rebase' because "
                     "'--no-patch' was passed.")
    finally:
        if current_branch is not None:
            execute_command('git checkout {0}'.format(current_branch),
                            cwd=directory)
    info("Working branch: " + ansi('boldon') + \
         str(get_current_branch()) + ansi('reset'))
    return 0
