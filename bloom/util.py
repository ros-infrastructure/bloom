# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Provides common utility functions for bloom.
"""

from __future__ import print_function

import argparse
import os
import sys

from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen

from bloom.logging import ansi
from bloom.logging import debug
from bloom.logging import disable_ANSI_colors
from bloom.logging import enable_debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr)
    sys.exit(1)


# Convention: < 0 is a warning exit, 0 is normal, > 0 is an error
class code(object):
    NOTHING_TO_DO = -10
    OK = 0
    UNKNOWN = 1
    ANSWERED_NO_TO_CONTINUE = 5
    NO_PACKAGE_XML_FOUND = 6
    NOT_A_GIT_REPOSITORY = 10
    NOT_ON_A_GIT_BRANCH = 11
    GIT_HAS_LOCAL_CHANGES = 12
    GIT_HAS_UNTRACKED_FILES = 13
    BRANCH_DOES_NOT_EXIST = 14
    INVALID_VERSION = 30
    INVALID_UPSTREAM_TAG = 31
    INVALID_BRANCH_ARGS = 40
    VCSTOOLS_NOT_FOUND = 50
    ROSDEP_NOT_FOUND = 51
    EMPY_NOT_FOUND = 52
    COULD_NOT_GET_PATCH_INFO = 60
    PATCHES_NOT_EXPORTED = 61
    COULD_NOT_TRIM = 62
    DEBIAN_MULTIPLE_PACKAGES_FOUND = 70
    DEBIAN_UNRECOGNIZED_BUILD_TYPE = 71
    DEBIAN_FAILED_TO_LOAD_TEMPLATE = 72
    DEBIAN_NO_SUCH_ROSDEP_KEY = 73
    DEBIAN_NO_ROSDEP_KEY_FOR_DISTRO = 74


class change_directory(object):
    def __init__(self, directory=''):
        self.directory = directory
        self.original_cwd = None

    def __enter__(self):
        self.original_cwd = os.getcwd()
        os.chdir(self.directory)
        return self.directory

    def __exit__(self, exc_type, exc_value, traceback):
        if self.original_cwd and os.path.exists(self.original_cwd):
            os.chdir(self.original_cwd)


def get_package_data(branch_name, directory=None):
    """
    Gets package data about the package(s) in the current branch.

    :param branch_name: name of the branch you are searching on (log use only)
    """
    debug("Looking for packages in '{0}'... ".format(branch_name), end='')
    ## Check for package.xml(s)
    repo_dir = directory if directory else os.getcwd()
    packages = find_packages(repo_dir)
    if type(packages) == dict and packages != {}:
        if len(packages) > 1:
            debug("found " + str(len(packages)) + " packages.",
                 use_prefix=False)
        else:
            debug("found '" + packages.values()[0].name + "'.",
                 use_prefix=False)
        version = verify_equal_package_versions(packages.values())
        return [p.name for p in packages.values()], version, packages
    ## Check for stack.xml
    has_rospkg = False
    try:
        import rospkg
        has_rospkg = True
    except ImportError:
        debug(ansi('redf') + "failed." + ansi('reset'), use_prefix=False)
        warning("rospkg was not detected, stack.xml discovery is disabled",
                file=sys.stderr)
    if not has_rospkg:
        error("no package.xml(s) found, and no name specified with "
              "'--package-name', aborting.", use_prefix=False)
        return code.NO_PACKAGE_XML_FOUND
    stack_path = os.path.join(repo_dir, 'stack.xml')
    if os.path.exists(stack_path):
        debug("found stack.xml.", use_prefix=False)
        stack = rospkg.stack.parse_stack_file(stack_path)
        return stack.name, stack.version, stack
    # Otherwise we have a problem
    debug("failed.", use_prefix=False)
    error("no package.xml(s) or stack.xml found, and not name "
          "specified with '--package-name', aborting.", use_prefix=False)
    return code.NO_PACKAGE_XML_FOUND


def add_global_arguments(parser):
    group = parser.add_argument_group('global')
    group.add_argument('-d', '--debug', help='enable debug messages',
                       action='store_true', default=False)
    group.add_argument('--pdb', help=argparse.SUPPRESS,
                       action='store_true', default=False)
    from bloom import __version__
    group.add_argument('--version', action='version', version=__version__,
                       help="prints the bloom version")
    group.add_argument('--no-color', action='store_true', default=False,
                       dest='no_color', help=argparse.SUPPRESS)
    add = group.add_argument
    add('--quiet', help=argparse.SUPPRESS,
        default=False, action='store_true')
    return parser

_pdb = False
_quiet = False


def handle_global_arguments(args):
    global _pdb, _quiet
    enable_debug(args.debug)
    _pdb = args.pdb
    _quiet = args.quiet
    if args.no_color:
        disable_ANSI_colors()


def print_exc(exc):
    exc_str = ''.join(exc)
    try:
        from pygments import highlight
        from pygments.lexers import PythonTracebackLexer
        from pygments.formatters import TerminalFormatter

        exc_str = highlight(exc_str, PythonTracebackLexer(),
                            TerminalFormatter())
    except ImportError:
        pass
    print(exc_str, file=sys.stderr)


def custom_exception_handler(type, value, tb):
    global _pdb
    # Print traceback
    import traceback
    print_exc(traceback.format_exception(type, value, tb))
    if not _pdb or hasattr(sys, 'ps1') or not sys.stderr.isatty():
        pass
    else:
        # ...then start the debugger in post-mortem mode.
        import pdb
        pdb.set_trace()


sys.excepthook = custom_exception_handler


def pdb_hook():
    global _pdb
    if _pdb:
        import pdb
        pdb.set_trace()


def check_output(cmd, cwd=None, stdin=None, stderr=None, shell=False):
    """Backwards compatible check_output"""
    p = Popen(cmd, cwd=cwd, stdin=stdin, stderr=stderr, shell=shell,
              stdout=PIPE)
    out, err = p.communicate()
    if p.returncode:
        raise CalledProcessError(p.returncode, cmd)
    return out


def create_temporary_directory(prefix_dir=None):
    """Creates a temporary directory and returns its location"""
    from tempfile import mkdtemp
    return mkdtemp(prefix='bloom_', dir=prefix_dir)


def maybe_continue(default='y'):
    """Prompts the user for continuation"""
    default = default.lower()
    msg = "{0}Continue ".format(ansi('boldon'))
    if default == 'y':
        msg += "{0}[Y/n]? {1}".format(ansi('yellowf'), ansi('reset'))
    else:
        msg += "{0}[y/N]? {1}".format(ansi('yellowf'), ansi('reset'))

    while True:
        response = raw_input(msg)
        if not response:
            response = default

        response = response.lower()
        if response not in ['y', 'n', 'q']:
            error_msg = 'Reponse `' + response + '` was not recognized, ' \
                        'please use one of y, Y, n, N.'
            error(error_msg)
        else:
            break

    if response in ['n', 'q']:
        return False
    return True


def extract_text(element):
    node_list = element.childNodes
    result = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            result.append(node.data)
    return ''.join(result)


def segment_version(full_version):
    version_list = full_version.split('.')
    if len(version_list) != 3:
        error('Invalid version element in the stack.xml, expected: ' \
              '<major>.<minor>.<patch>')
        sys.exit(code.INVALID_VERSION)
    return version_list


def execute_command(cmd, shell=True, autofail=True, silent=True,
                    silent_error=False, cwd=None, return_io=False):
    """
    Executes a given command using vcstools' run_shell_command function.
    """
    io_type = None
    result = 0
    if silent:
        io_type = PIPE
    debug(((cwd) if cwd else os.getcwd()) + ":$ " + str(cmd))
    p = Popen(cmd, shell=True, cwd=cwd, stdout=io_type, stderr=io_type)
    out, err = p.communicate()
    result = p.returncode
    if result != 0:
        if not silent_error:
            error("'execute_command' failed to call '{0}'".format(cmd) + \
                  " which had a return code ({0}):".format(result))
            if out:
                error("    stdout:\n" + ansi('reset') + str(out))
                error("end stdout")
            if err:
                error("    stderr:\n" + ansi('reset') + str(err))
                error("end stderr")
        if autofail:
            raise CalledProcessError(cmd=cmd, output=out, returncode=result)
    if return_io:
        return result, out, err
    else:
        return result


def get_versions_from_upstream_tag(tag):
    """
    Returns the [major, minor, patch] version list given an upstream tag.
    """
    tag_version = tag.split('/')
    if len(tag_version) != 2:
        error("Malformed tag {0}".format(tag))
        sys.exit(code.INVALID_UPSTREAM_TAG)
    tag_version = tag_version[1]
    return segment_version(tag_version)
