# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Willow Garage, Inc.
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
import shutil
import socket
import sys
import tempfile
import time

try:
    # Python2
    from urllib2 import HTTPError
    from urllib2 import URLError
    from urllib2 import urlopen
except ImportError:
    # Python3
    from urllib.error import HTTPError
    from urllib.error import URLError
    from urllib.request import urlopen

from email.utils import formatdate

from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import STDOUT
from subprocess import Popen

try:
    # Python2
    from StringIO import StringIO
except ImportError:
    # Python3
    from io import StringIO

from bloom.logging import debug
from bloom.logging import disable_ANSI_colors
from bloom.logging import enable_debug
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import sanitize
from bloom.logging import warning

try:
    to_unicode = unicode
except NameError:
    to_unicode = str


def flush_stdin():
    try:
        from termios import tcflush, TCIFLUSH
        tcflush(sys.stdin, TCIFLUSH)
    except ImportError:
        # fallback if not supported on some platforms
        pass

if sys.version_info < (3, 0):
    def safe_input(prompt=None):
        flush_stdin()
        return raw_input(prompt)
else:
    def safe_input(prompt=None):
        flush_stdin()
        return input(prompt)


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
    ROSDEP_FAILED = 53
    COULD_NOT_GET_PATCH_INFO = 60
    PATCHES_NOT_EXPORTED = 61
    COULD_NOT_TRIM = 62
    GENERATOR_MULTIPLE_PACKAGES_FOUND = 70
    GENERATOR_UNRECOGNIZED_BUILD_TYPE = 71
    GENERATOR_FAILED_TO_LOAD_TEMPLATE = 72
    GENERATOR_NO_SUCH_ROSDEP_KEY = 73
    GENERATOR_NO_ROSDEP_KEY_FOR_DISTRO = 74
    GENERATOR_INVALID_INSTALLER_KEY = 75


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


class redirected_stdio(object):
    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = out = StringIO()
        sys.stderr = err = StringIO()
        return out, err

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


class temporary_directory(object):
    def __init__(self, prefix=''):
        self.prefix = prefix

    def __enter__(self):
        self.original_cwd = os.getcwd()
        self.temp_path = tempfile.mkdtemp(prefix=self.prefix)
        os.chdir(self.temp_path)
        return self.temp_path

    def __exit__(self, exc_type, exc_value, traceback):
        if self.temp_path and os.path.exists(self.temp_path):
            shutil.rmtree(self.temp_path)
        if self.original_cwd and os.path.exists(self.original_cwd):
            os.chdir(self.original_cwd)


def get_rfc_2822_date(date):
    return formatdate(float(date.strftime("%s")), date.tzinfo)


def load_url_to_file_handle(url, retry=2, retry_period=1, timeout=10):
    """Loads a given url with retries, retry_periods, and timeouts

    Based on https://github.com/ros-infrastructure/rosdistro/blob/master/src/rosdistro/loader.py

    :param url: URL to load and return contents of
    :type url: str
    :param retry: number of times to retry the url on 503 or timeout
    :type retry: int
    :param retry_period: time to wait between retries in seconds
    :type: retry_period: float
    :param timeout: timeout for opening the URL in seconds
    :type timeout: float
    """
    try:
        fh = urlopen(url, timeout=timeout)
    except HTTPError as e:
        if e.code == 503 and retry:
            time.sleep(retry_period)
            return load_url_to_file_handle(url,
                                           retry=retry - 1,
                                           retry_period=retry_period,
                                           timeout=timeout)
        e.msg += ' (%s)' % url
        raise
    except URLError as e:
        if isinstance(e.reason, socket.timeout) and retry:
            time.sleep(retry_period)
            return load_url_to_file_handle(url,
                                           retry=retry - 1,
                                           retry_period=retry_period,
                                           timeout=timeout)
        raise URLError(str(e) + ' (%s)' % url)
    return fh


def my_copytree(tree, destination, ignores=None):
    ignores = ignores or []
    if os.path.exists(destination):
        if not os.path.isdir(destination):
            raise RuntimeError("Destination exists and is not a directory: '{0}'".format(destination))
    else:
        os.makedirs(destination)
    for item in os.listdir(tree):
        if item in ignores:
            continue
        src = os.path.join(tree, item)
        dst = os.path.join(destination, item)
        if os.path.islink(src):
            linkto = os.readlink(src)
            os.symlink(linkto, dst)
        elif os.path.isdir(src):
            my_copytree(src, dst, ignores)
        elif os.path.isfile(src):
            shutil.copy(src, dst)
        else:
            raise RuntimeError("Unknown file type for element: '{0}'".format(src))


def add_global_arguments(parser):
    from bloom import __version__
    group = parser.add_argument_group('global')
    add = group.add_argument
    add('-d', '--debug', help='enable debug messages',
        action='store_true', default=False)
    add('--pdb', help=argparse.SUPPRESS,
        action='store_true', default=False)
    add('--version', action='version', version=__version__,
        help="prints the bloom version")
    add('--no-color', action='store_true', default=False,
        dest='no_color', help=argparse.SUPPRESS)
    add('--quiet', help=argparse.SUPPRESS,
        default=False, action='store_true')
    add('--unsafe', default=False, action='store_true',
        help="Makes bloom faster, but if there is an error then you could run into trouble.")
    return parser

_pdb = False
_quiet = False
_disable_git_clone = False
_disable_git_clone_quiet = False
_distro_list_prompt = [
    'indigo',
    'kinetic',
    'lunar',
    'melodic',
]


def disable_git_clone(state=True):
    global _disable_git_clone
    _disable_git_clone = state
    if state:
        os.environ['BLOOM_UNSAFE'] = "1"
    elif 'BLOOM_UNSAFE' in os.environ:
        del os.environ['BLOOM_UNSAFE']


def quiet_git_clone_warning(state=True):
    global _disable_git_clone_quiet
    _disable_git_clone_quiet = state
    if state:
        os.environ['BLOOM_UNSAFE_QUIET'] = "1"
    elif 'BLOOM_UNSAFE_QUIET' in os.environ:
        del os.environ['BLOOM_UNSAFE_QUIET']


def get_git_clone_state():
    global _disable_git_clone
    return _disable_git_clone


def get_distro_list_prompt():
    global _distro_list_prompt
    return ', '.join(_distro_list_prompt)


def get_git_clone_state_quiet():
    global _disable_git_clone_quiet
    return _disable_git_clone_quiet


def handle_global_arguments(args):
    global _pdb, _quiet
    enable_debug(args.debug or 'DEBUG' in os.environ)
    _pdb = args.pdb
    _quiet = args.quiet
    if args.no_color:
        disable_ANSI_colors()
    disable_git_clone(args.unsafe or 'BLOOM_UNSAFE' in os.environ)
    quiet_git_clone_warning('BLOOM_UNSAFE_QUIET' in os.environ)


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
    info(exc_str, file=sys.stderr, use_prefix=False)


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


def __get_env_for_cmd(cmd):
    executable = None
    if isinstance(cmd, list) or isinstance(cmd, tuple):
        executable = cmd[0]
    if isinstance(cmd, str) or isinstance(cmd, to_unicode):
        executable = cmd.split()[0]
    env = None
    if executable is not None and executable.startswith('git'):
        env = os.environ
        # If the output is from git, force lang to C to prevent output in different languages.
        env['LC_ALL'] = 'C'
    return env


def check_output(cmd, cwd=None, stdin=None, stderr=None, shell=False):
    """Backwards compatible check_output"""
    env = __get_env_for_cmd(cmd)
    p = Popen(cmd, cwd=cwd, stdin=stdin, stderr=stderr, shell=shell,
              stdout=PIPE, env=env)
    out, err = p.communicate()
    if p.returncode:
        raise CalledProcessError(p.returncode, cmd)
    if not isinstance(out, str):
        out = out.decode('utf-8')
    return out


def create_temporary_directory(prefix_dir=None):
    """Creates a temporary directory and returns its location"""
    from tempfile import mkdtemp
    return mkdtemp(prefix='bloom_', dir=prefix_dir)


def maybe_continue(default='y', msg='Continue'):
    """Prompts the user for continuation"""
    default = default.lower()
    msg = "@!{msg} ".format(msg=sanitize(msg))
    if default == 'y':
        msg += "@{yf}[Y/n]? @|"
    else:
        msg += "@{yf}[y/N]? @|"
    msg = fmt(msg)

    while True:
        response = safe_input(msg)
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
        warning('Invalid version element, expected: '
                '<major>.<minor>.<patch>')
    if len(version_list) < 3:
        sys.exit(code.INVALID_VERSION)
    return version_list


def execute_command(cmd, shell=True, autofail=True, silent=True,
                    silent_error=False, cwd=None, return_io=False):
    """
    Executes a given command using Popen.
    """
    out_io = None
    err_io = None
    result = 0
    if silent:
        out_io = PIPE
        err_io = STDOUT
    debug(((cwd) if cwd else os.getcwd()) + ":$ " + str(cmd))
    env = __get_env_for_cmd(cmd)
    p = Popen(cmd, shell=shell, cwd=cwd, stdout=out_io, stderr=err_io, env=env)
    out, err = p.communicate()
    if out is not None and not isinstance(out, str):
        out = out.decode('utf-8')
    if err is not None and not isinstance(err, str):
        err = err.decode('utf-8')
    result = p.returncode
    if result != 0:
        if not silent_error:
            error("'execute_command' failed to call '{0}'".format(cmd) +
                  " which had a return code ({0}):".format(result))
            error("```")
            info(out, use_prefix=False)
            error("```")
        if autofail:
            raise CalledProcessError(result, cmd)
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
