from __future__ import print_function

from .. util import execute_command
from .. util import maybe_continue
from .. logging import ansi
from .. logging import error
from .. logging import info
from .. git import create_branch
from .. git import get_branches
from .. git import get_current_branch
from .. git import track_branches


def execute_branch(src, dst, patch, interactive, pretend, directory=None):
    """
    executes bloom branch from src to dst and optionally will patch

    Copies the current branch (or specified source branch) to a destination
    branch. If the destination branch does not exist, then it is created
    first. Additionally, if the DST_BRANCH/patches doesn't exist it is
    created. If the DST_BRANCH/patches branch already exists, the patches in
    the branch are applied to the new commit in the DST_BRANCH branch. If this
    command is successful the working branch will be set to the DST_BRANCH,
    otherwise the original working branch will be restored.

    :param src: source branch from which to copy
    :param dst: destination branch to copy to
    :param patch: whether or not to apply previous patches to destination
    :param interactive: if True actions are summarized before committing
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

    if interactive or pretend:
        info("Summary of changes:")
        if create_dst_branch:
            info("  The specified destination branch, " + ansi('boldon') + \
                 dst + ansi('reset') + ", does not exist, it will be " + \
                 "created from the source branch " + ansi('boldon') + src + \
                 ansi('reset'))
        info("  The working branch will be set to " + ansi('boldon') + dst + \
             ansi('reset'))
        if pretend:
            info("Exiting because this is pretend mode.")
            return 0
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
        current_branch = None
    finally:
        if current_branch is not None:
            execute_command('git checkout {0}'.format(current_branch),
                            cwd=directory)
    return 0
