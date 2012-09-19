from __future__ import print_function

import sys
import traceback
from argparse import ArgumentParser
from subprocess import CalledProcessError

from .. logging import error
from .. git import get_current_branch, get_root

from . branch import execute_branch


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(
        description="""\
If the DST_BRANCH does not exist yet, then it is created by branching the
current working branch or the specified SRC_BRANCH.

If the patches/DST_BRANCH branch does not exist yet then it is created.

If the branches are created successful, then the working branch will be set to
the DST_BRANCH, otherwise the working branch will remain unchanged.

If the DST_BRANCH and patches/DST_BRANCH already existed, then a call to `git-
bloom-patch rebase` is attempted unless '--no-patch' is passed.
"""
    )
    add = parser.add_argument
    add('--src', '-s', metavar='SRC_BRANCH',
        help="(optional) specifies the branch to copy from")
    add('--no-patch', '-n', dest='patch',
                        help="skips application of previous patches",
                        action='store_false',
                        default=True)
    add('--interactive', '-i', dest='interactive',
                        help="asks before committing any changes",
                        action='store_true',
                        default=False)
    add('--pretend', '-p', dest='pretend',
                        help="summarizes the changes and exits",
                        action='store_true',
                        default=False)
    add('dst', metavar="DST_BRANCH", help="name of destination branch")
    return parser


def branchmain():
    parser = get_parser()
    args = parser.parse_args()
    retcode = 0
    try:
        # Assert this is a git repository
        assert get_root() != None, "Not in a valid git repository."
        # If the src argument isn't set, use the current branch
        if args.src is None:
            args.src = get_current_branch()
        # Execute the branching
        retcode = execute_branch(args.src, args.dst, args.patch,
                                 args.interactive, args.pretend)
    except CalledProcessError as err:
        # No need for a trackback here, a git call probably failed
        traceback.print_exc()
        error(str(err))
        retcode = 1
    except Exception as err:
        # Unhandled exception, print traceback
        traceback.print_exc()
        error(str(err))
        retcode = 2
    sys.exit(retcode)
