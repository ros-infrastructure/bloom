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

import sys
import os

from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen

from . logging import ansi
from . logging import debug
from . logging import enable_debug
from . logging import error
from . logging import info

try:
    import rospkg.stack
except ImportError:
    error("rospkg was not detected, please install it.", file=sys.stderr)
    sys.exit(1)


def add_global_arguments(parser):
    group = parser.add_argument_group('global')
    group.add_argument('-d', '--debug', help='enable debug messages',
                       action='store_true', default=False)
    group.add_argument('--pdb', help='enable debugging post mortem with pdb',
                       action='store_true', default=False)
    group.add_argument('--version', action='store_true', default=False,
                       help="prints the bloom version")
    return parser

_pdb = False


def handle_global_arguments(args):
    global _pdb
    enable_debug(args.debug)
    _pdb = args.pdb
    if args.version:
        from bloom import __version__
        print(__version__)
        sys.exit(0)


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
        if response not in ['y', 'n']:
            error_msg = 'Reponse `' + response + '` was not recognized, ' \
                        'please use one of y, Y, n, N.'
            error(error_msg)
        else:
            break

    if response == 'n':
        return False
    return True


def bailout(reason='Exiting.'):
    """Exits bloom for a given reason"""
    error(reason)
    sys.exit(1)


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
        bailout('Invalid version element in the stack.xml, expected: ' \
                '<major>.<minor>.<patch>')
    return version_list


def parse_stack_xml(file_path):
    """
    Returns a dictionary representation of a stack xml file.

    :param file_path: path to stack xml file to be converted
    :returns: dictionary representation of the stack xml file
    """
    return rospkg.stack.parse_stack_file(file_path)


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
        bailout("Malformed tag {0}".format(tag))
    tag_version = tag_version[1]
    return segment_version(tag_version)
