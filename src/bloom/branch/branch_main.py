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
        description="Copies the current branch (or specified source branch) "
                    "to a destination branch. If the destination branch does "
                    "not exist, then it is created first. Additionally, if "
                    "the DST_BRANCH/patches doesn't exist it is created. If "
                    "the DST_BRANCH/patches branch already exists, the "
                    "patches in the branch are applied to the new commit in "
                    "the DST_BRANCH branch. If this command is successful the "
                    "working branch will be set to the DST_BRANCH, otherwise "
                    "the original working branch will be restored."
    )
    add = parser.add_argument
    add('--src', '-s', metavar='SRC_BRANCH',
        help="(optional) specifies the branch to copy from")
    add('--no-patch', '-n', dest='patch',
                        help="skips application of previous patches",
                        action='store_false',
                        default=True)
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
        execute_branch(args.src, args.dst, args.patch)
    except CalledProcessError as err:
        # No need for a trackback here, a git call probably failed
        error(err)
        retcode = 1
    except Exception as err:
        # Unhandled exception, print traceback
        traceback.print_exc()
        error(err)
        retcode = 2
    sys.exit(retcode)
