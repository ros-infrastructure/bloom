from __future__ import print_function

import sys
from argparse import ArgumentParser


def export_patches(base_branch, cwd=None, src_branch=None):
    print(base_branch)


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = ArgumentParser(
        description="""\
Exports the commits that have been made on the current branch since the
specified BASE_BRANCH to a patches branch, which is named
'patches/<current branch name>', using git format-patch.
"""
    )
    add = parser.add_argument
    add('base', metavar="BASE_BRANCH", help="name of branch to patch since")
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    args = parser.parse_args(sysargs)
    return export_patches(args.base)
