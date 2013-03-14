from __future__ import print_function

import argparse
import sys
import traceback
from subprocess import CalledProcessError

from bloom.git import ensure_git_root
from bloom.git import get_root

from bloom.logging import error

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments
from bloom.util import print_exc

from bloom.commands.git.patch import export_cmd
from bloom.commands.git.patch import import_cmd
from bloom.commands.git.patch import remove_cmd
from bloom.commands.git.patch import rebase_cmd
from bloom.commands.git.patch import trim_cmd


def get_argument_parser():
    parser = argparse.ArgumentParser(
        description="Configures the bloom repository with information in groups called tracks.")
    metavar = "[export|import|remove|rebase|trim]"
    subparsers = parser.add_subparsers(
        title="Commands",
        metavar=metavar,
        description="Call `git-bloom-patch {0} -h` for additional help information on each command.".format(metavar))
    export_cmd.add_parser(subparsers)
    import_cmd.add_parser(subparsers)
    remove_cmd.add_parser(subparsers)
    rebase_cmd.add_parser(subparsers)
    trim_cmd.add_parser(subparsers)
    return parser


def main(sysargs=None):
    parser = get_argument_parser()
    add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    retcode = "command not run"
    if get_root() is None:
        parser.print_help()
        error("This command must be run in a valid git repository.", exit=True)
    ensure_git_root()
    try:
        retcode = args.func(args) or 0
    except CalledProcessError as err:
        # Problem calling out to git probably
        print_exc(traceback.format_exc())
        error(str(err))
        retcode = 2
    except Exception as err:
        # Unhandled exception, print traceback
        print_exc(traceback.format_exc())
        error(str(err))
        retcode = 3
    sys.exit(retcode)
