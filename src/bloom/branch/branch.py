from __future__ import print_function


def execute_branch(src, dst, patch, interactive, pretend):
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
    """
    # If source branch exists
        # If source branch is remote, track it
    # Else
        # Error

    # If destination branch exists
        # If destination branch is remote
            # Track it
    # Else
        # Set create_destination_branch = True

    # If destination patches branch exists
        # If create_destination_branch == True
            # This shouldn't happen, Error
        # Else
            # If destination patches branch is remote
                # Track it
    # Else
        # Set create_destination_patches_branch = True

    # If interactive or pretend
        # Summarize changes
        # If pretend
            # Exit
        # Ask use if they want to continue
        # If no
            # Exit

    # If create_destination_branch
        # git branch 'source branch' 'destination_branch'
    # If create_destination_patches_branch
        # bloom.git.create_branch('source branch'+'/patches', orphaned=True)

    # Attempt to merge source branch from destination branch
    # Try:
        # git merge -s theirs 'source branch'
    # Except subprocess.CalledProcessError:
        # drop out, there was a conflict
    pass
