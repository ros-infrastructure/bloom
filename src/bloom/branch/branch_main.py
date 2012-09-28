from __future__ import print_function

import sys
import traceback
import argparse
from subprocess import CalledProcessError

from .. git import get_current_branch, get_root
from .. logging import ansi
from .. logging import error
from .. logging import info
from .. util import add_global_arguments
from .. util import handle_global_arguments
from .. util import print_exc

from . branch import branch_packages


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = argparse.ArgumentParser(description="""\
If the DST_BRANCH does not exist yet, then it is created by branching the
current working branch or the specified SRC_BRANCH.

If the patches/DST_BRANCH branch does not exist yet then it is created.

If the branches are created successful, then the working branch will be set to
the DST_BRANCH, otherwise the working branch will remain unchanged.

If the DST_BRANCH and patches/DST_BRANCH already existed, then a call to
`git-bloom-patch rebase` is attempted unless '--no-patch' is passed.
""", formatter_class=argparse.RawTextHelpFormatter)
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
    add('prefix', metavar="DST_BRANCH_PREFIX",
        help="prefix of destination branch\ni.e. DST_BRANCH becomes\n"
             "DST_BRANCH_PREFIX/<package_name>")
    add('--continue-on-error', '-c',
        help="continues branching packages even on errors",
        action='store_true', default=False)
    return parser


def branchmain():
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
                                  args.interactive, args.continue_on_error)
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
