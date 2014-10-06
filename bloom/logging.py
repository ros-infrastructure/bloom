# -*- coding: utf-8 -*-
# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Open Source Robotics Foundation, Inc.
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
#  * Neither the name of Open Source Robotics Foundation, Inc. nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
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

from __future__ import print_function
from __future__ import unicode_literals

import atexit
import datetime
import os
from platform import mac_ver
try:
    from pkg_resources import parse_version
except OSError:
    os.chdir(os.path.expanduser('~'))
    from pkg_resources import parse_version
import re
import string
import sys

import functools

_ansi = {}
_quiet = False
_debug = False
_log_prefix_stack = ['']
_log_prefix = ''
_log_indent = False
_drop_first_log_prefix = False

_emoji_check_mark = "✅  "
_emoji_cross_mark = "❌  "
_is_mac_lion_or_greater = parse_version(mac_ver()[0]) >= parse_version('10.7.0')


def ansi(key):
    """Returns the escape sequence for a given ansi color key"""
    global _ansi
    return _ansi[key]

_strip_ansi_re = re.compile(r'\033\[[0-9;m]*')


def strip_ansi(msg):
    return _strip_ansi_re.sub('', msg)


def enable_ANSI_colors():
    """
    Populates the global module dictionary `ansi` with ANSI escape sequences.
    """
    global _ansi
    color_order = [
        'black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white'
    ]
    short_colors = {
        'black': 'k', 'red': 'r', 'green': 'g', 'yellow': 'y', 'blue': 'b',
        'purple': 'p', 'cyan': 'c', 'white': 'w'
    }
    _ansi = {
        'escape': '\033', 'reset': 0, '|': 0,
        'boldon': 1, '!': 1, 'italicson': 3, '/': 3, 'ulon': 4, '_': 4,
        'invon': 7, 'boldoff': 22, 'italicsoff': 23,
        'uloff': 24, 'invoff': 27
    }

    # Convert plain numbers to escapes
    for key in _ansi:
        if key != 'escape':
            _ansi[key] = '{0}[{1}m'.format(_ansi['escape'], _ansi[key])

    # Foreground
    for index, color in enumerate(color_order):
        _ansi[color] = '{0}[{1}m'.format(_ansi['escape'], 30 + index)
        _ansi[color + 'f'] = _ansi[color]
        _ansi[short_colors[color] + 'f'] = _ansi[color + 'f']

    # Background
    for index, color in enumerate(color_order):
        _ansi[color + 'b'] = '{0}[{1}m'.format(_ansi['escape'], 40 + index)
        _ansi[short_colors[color] + 'b'] = _ansi[color + 'b']

    # Fmt sanitizers
    _ansi['atexclimation'] = '@!'
    _ansi['atfwdslash'] = '@/'
    _ansi['atunderscore'] = '@_'
    _ansi['atbar'] = '@|'


def disable_ANSI_colors():
    """
    Sets all the ANSI escape sequences to empty strings, effectively disabling
    console colors.
    """
    global _ansi
    for key in _ansi:
        _ansi[key] = ''


def is_mac_lion_or_greater():
    global _is_mac_lion_or_greater
    return _is_mac_lion_or_greater


def get_success_prefix():
    return _emoji_check_mark if _is_mac_lion_or_greater else "@{gf}<== @|"


def get_error_prefix():
    return _emoji_cross_mark if _is_mac_lion_or_greater else "@{rf}@!<== @|"


# Default to ansi colors on
enable_ANSI_colors()


def quiet(state=True):
    global _quiet
    _quiet = state

# Default to quiet off
quiet(False)


def enable_debug(state=True):
    global _debug
    _debug = state


def is_debug():
    global _debug
    return _debug

# Default to debug off
enable_debug('DEBUG' in os.environ)


def enable_debug_indent(state=True):
    global _log_indent
    _log_indent = state

enable_debug_indent(True)


def enable_drop_first_log_prefix(state=True):
    global _drop_first_log_prefix
    _drop_first_log_prefix = state

enable_drop_first_log_prefix(True)


def _get_log_prefix():
    global _log_prefix_stack, _log_indent
    if _log_indent:
        return (' ' * (len(_log_prefix_stack) - 2)) + _log_prefix_stack[-1]
    else:
        return _log_prefix_stack[-1]


def push_log_prefix(prefix):
    global _log_prefix, _log_prefix_stack, _drop_first_log_prefix
    if _drop_first_log_prefix and len(_log_prefix_stack) <= 1:
        _log_prefix_stack.append('')
    else:
        _log_prefix_stack.append(prefix)
    _log_prefix = _get_log_prefix()


def pop_log_prefix():
    global _log_prefix, _log_prefix_stack
    if len(_log_prefix_stack) > 1:
        _log_prefix_stack.pop()
    _log_prefix = _get_log_prefix()


class ContextDecorator(object):
    def __call__(self, f):
        @functools.wraps(f)
        def decorated(*args, **kwds):
            with self:
                return f(*args, **kwds)
        return decorated


class log_prefix(ContextDecorator):
    def __init__(self, prefix):
        self.prefix = prefix

    def __enter__(self):
        push_log_prefix(self.prefix)

    def __exit__(self, exc_type, exc_value, traceback):
        pop_log_prefix()

_file_log = None


def debug(msg, file=None, end='\n', use_prefix=True):
    file = file if file is not None else sys.stdout
    global _quiet, _debug, _log_prefix, _file_log
    msg = '{0}'.format(msg)
    if use_prefix:
        msg = ansi('greenf') + _log_prefix + msg + ansi('reset')
    else:
        msg = ansi('greenf') + msg + ansi('reset')
    if not _quiet and _debug:
        print(msg, file=file, end=end)
    if _file_log is not None:
        print(('[debug] ' + strip_ansi(msg)).encode('UTF-8'), file=_file_log, end=end)
    return msg


def info(msg, file=None, end='\n', use_prefix=True):
    file = file if file is not None else sys.stdout
    global _quiet, _log_prefix, _file_log
    msg = '{0}'.format(msg)
    if use_prefix:
        msg = _log_prefix + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file, end=end)
    if _file_log is not None:
        print(('[info] ' + strip_ansi(msg)).encode('UTF-8'), file=_file_log, end=end)
    return msg


def warning(msg, file=None, end='\n', use_prefix=True):
    file = file if file is not None else sys.stdout
    global _quiet, _log_prefix, _file_log
    msg = '{0}'.format(msg)
    if use_prefix:
        msg = ansi('yellowf') + _log_prefix + msg \
            + ansi('reset')
    else:
        msg = ansi('yellowf') + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file, end=end)
    if _file_log is not None:
        print(('[warning] ' + strip_ansi(msg)).encode('UTF-8'), file=_file_log, end=end)
    return msg


def error(msg, file=None, end='\n', use_prefix=True, exit=False):
    file = file if file is not None else sys.stderr
    global _quiet, _log_prefix, _file_log
    msg = '{0}'.format(msg)
    if use_prefix:
        msg = ansi('redf') + ansi('boldon') + _log_prefix + msg + ansi('reset')
    else:
        msg = ansi('redf') + ansi('boldon') + msg + ansi('reset')
    if _file_log is not None:
        print(('[error] ' + strip_ansi(msg)).encode('UTF-8'), file=_file_log, end=end)
    if exit:
        if _file_log is not None:
            print("[error] SYS.EXIT", file=_file_log, end=end)
        sys.exit(msg)
    if not _quiet:
        print(msg, file=file, end=end)
    return msg

try:
    _log_id = os.environ.get('BLOOM_LOGGING_ID', str(os.getpid()))
    os.environ['BLOOM_LOGGING_ID'] = _log_id  # Store in env for subprocess
    _file_log_prefix = os.path.join(os.path.expanduser('~'), '.bloom_logs')
    if not os.path.isdir(_file_log_prefix):
        os.makedirs(_file_log_prefix)
    _file_log_path = os.path.join(_file_log_prefix, _log_id + '.log')
    _file_log = open(_file_log_path, 'a')
    if str(os.getpid()) == _log_id:
        import bloom
        _file_log.write("[bloom] bloom version " + bloom.__version__ + "\n")
except Exception as exc:
    _file_log = None
    error("Logging is not working: {0}: {1}".format(exc.__class__.__name__, exc))

_summary_file = None


def _get_summary_file_path():
    global _summary_file, _file_log_prefix, _log_id
    if _summary_file is None:
        _summary_file = os.path.join(_file_log_prefix, _log_id + '.summary')
    return _summary_file


@atexit.register
def close_logging():
    global _file_log, _summary_file
    if _file_log is not None:
        name = _file_log.name
        _file_log.close()
        _file_log = None
        if str(os.getpid()) == os.path.basename(name).split('.')[0]:
            new_name = str(datetime.datetime.now())
            new_name = new_name.replace(' ', '_').replace(':', '.') + '.log'
            new_name = os.path.basename(str(sys.argv[0])) + "_" + new_name
            new_name = os.path.join(os.path.dirname(name), new_name)
            os.rename(name, new_name)
            if os.path.exists(name):
                os.remove(name)


class ColorTemplate(string.Template):
    delimiter = '@'


def sanitize(msg):
    """Sanitizes the existing msg, use before adding color annotations"""
    msg = msg.replace('@', '@@')
    msg = msg.replace('{', '{{')
    msg = msg.replace('}', '}}')
    msg = msg.replace('@@!', '@{atexclimation}')
    msg = msg.replace('@@/', '@{atfwdslash}')
    msg = msg.replace('@@_', '@{atunderscore}')
    msg = msg.replace('@@|', '@{atbar}')
    return msg


def fmt(msg):
    """Replaces color annotations with ansi escape sequences"""
    global _ansi
    msg = msg.replace('@!', '@{boldon}')
    msg = msg.replace('@/', '@{italicson}')
    msg = msg.replace('@_', '@{ulon}')
    msg = msg.replace('@|', '@{reset}')
    t = ColorTemplate(msg)
    msg = t.substitute(_ansi) + ansi('reset')
    msg = msg.replace('{{', '{')
    msg = msg.replace('}}', '}')
    return msg
