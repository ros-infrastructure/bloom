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

from subprocess import check_call, CalledProcessError, PIPE
from subprocess import Popen

from . logging import enable_debug
from . logging import error
from . logging import debug
from . logging import info

try:
    import rospkg.stack
except ImportError:
    error("rospkg was not detected, please install it.", file=sys.stderr)
    sys.exit(1)

_ansi = {}


def add_global_arguments(parser):
    group = parser.add_argument_group('global')
    group.add_argument('-d', '--debug', help='enable debug messages',
                       action='store_true', default=False)
    return parser


def handle_global_arguments(args):
    enable_debug(args.debug)


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


def ansi(key):
    """Returns the escape sequence for a given ansi color key"""
    global _ansi
    return _ansi[key]


def enable_ANSI_colors():
    """
    Populates the global module dictionary `ansi` with ANSI escape sequences.
    """
    global _ansi
    colors = [
        'black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white'
    ]
    _ansi = {
        'escape': '\033', 'reset': 0,
        'boldon': 1, 'italicson': 3, 'ulon': 4, 'invon': 7,
        'boldoff': 22, 'italicsoff': 23, 'uloff': 24, 'invoff': 27,
    }

    # Convert plain numbers to escapes
    for key in _ansi:
        if key != 'escape':
            _ansi[key] = '{0}[{1}m'.format(_ansi['escape'], _ansi[key])

    # Foreground
    for index, color in enumerate(colors):
        _ansi[color + 'f'] = '{0}[{1}m'.format(_ansi['escape'], 30 + index)

    # Background
    for index, color in enumerate(colors):
        _ansi[color + 'b'] = '{0}[{1}m'.format(_ansi['escape'], 40 + index)


def disable_ANSI_colors():
    """
    Sets all the ANSI escape sequences to empty strings, effectively disabling
    console colors.
    """
    global _ansi
    for key in _ansi:
        _ansi[key] = ''

enable_ANSI_colors()


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


def execute_command(cmd, shell=True, autofail=True, silent=True, cwd=None):
    """
    Executes a given command using vcstools' run_shell_command function.
    """
    io_type = None
    result = 0
    if silent:
        io_type = PIPE
    try:
        debug(((cwd) if cwd else os.getcwd()) + ":$ " + str(cmd))
        result = check_call(cmd, shell=True, cwd=cwd,
                            stdout=io_type, stderr=io_type)
    except CalledProcessError as cpe:
        result = cpe.returncode
        if autofail:
            raise
    return result


def assert_is_remote_git_repo(repo):
    """
    Asserts that the specified repo url points to a valid git repository.
    """
    info('Verifying that {0} is a git repository...'.format(repo), end='')
    cmd = 'git ls-remote --heads {0}'.format(repo)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, _ = p.communicate()
    if p.returncode != 0:
        info(ansi('redf') + ' fail' + ansi('reset'), use_prefix=False)
        bailout("Repository {0} is not a valid git repository.".format(repo))
    else:
        info(' pass', use_prefix=False)


def assert_is_not_gbp_repo(repo):
    """
    Asserts that the specified repo url does not point to a gbp repo.
    """
    assert_is_remote_git_repo(repo)
    info('Verifying that {0} is not a gbp repository...'.format(repo), end='')
    cmd = 'git ls-remote --heads {0} upstream*'.format(repo)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, _ = p.communicate()
    if p.returncode == 0 and len(output) > 0:
        info(ansi('redf') + ' fail' + ansi('reset'), use_prefix=False)
        bailout("Error: {0} appears to have an 'upstream' branch, " \
                "indicating a gbp.".format(repo))
    else:
        info(' pass', use_prefix=False)


def get_versions_from_upstream_tag(tag):
    """
    Returns the [major, minor, patch] version list given an upstream tag.
    """
    tag_version = tag.split('/')
    if len(tag_version) != 2:
        bailout("Malformed tag {0}".format(tag))
    tag_version = tag_version[1]
    return segment_version(tag_version)
