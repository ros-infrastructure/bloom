from __future__ import print_function

import sys
import os
import traceback
from subprocess import CalledProcessError

from .. logging import error
from .. git import get_root

from . import export_cmd
from . import import_cmd
from . import remove_cmd
from . import rebase_cmd
from . import trim_cmd


def usage(exit=True):
    print("""\
git-bloom-patch is a patch management tool.

Commands:
    git-bloom-patch export
        Exports the current changesets to the patches branch

    git-bloom-patch import
        Imports and applys the patches from the patches branch

    git-bloom-patch remove
        Removes any patches that have been applied (even non-exported ones)

    git-bloom-patch rebase
        Rebases any applied patches after merging from the source branch

    git-bloom-patch trim
        Moves a given sub directory into the root of the git repository

For more information on individual commands type, git-bloom-patch <cmd> -h
""")
    if exit:
        sys.exit(getattr(os, 'EX_USAGE', 1))


def patchmain():
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        error("You must specify a command, e.g. git-bloom-patch <command>")
        usage()
    if get_root() == None:

        error("This command must be run in a valid git repository.")
        usage()
    try:
        if command == "export":
            retcode = export_cmd.main()
        elif command == "import":
            retcode = import_cmd.main()
        elif command == "remove":
            retcode = remove_cmd.main()
        elif command == "rebase":
            retcode = rebase_cmd.main()
        elif command == "trim":
            retcode = trim_cmd.main()
        else:
            error("Invalid command specified: {0}".format(command))
            usage(False)
            retcode = 1
    except CalledProcessError as err:
        # Problem calling out to git probably
        traceback.print_exc()
        error(str(err))
        retcode = 2
    except Exception as err:
        # Unhandled exception, print traceback
        traceback.print_exc()
        error(str(err))
        retcode = 3
    sys.exit(retcode)
