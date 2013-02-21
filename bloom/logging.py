from __future__ import print_function

import os
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


def ansi(key):
    """Returns the escape sequence for a given ansi color key"""
    global _ansi
    return _ansi[key]


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


def debug(msg, file=None, end='\n', use_prefix=True):
    file = file if file is not None else sys.stdout
    global _quiet, _debug, _log_prefix
    msg = str(msg)
    if use_prefix:
        msg = ansi('greenf') + _log_prefix + msg + ansi('reset')
    else:
        msg = ansi('greenf') + msg + ansi('reset')
    if not _quiet and _debug:
        print(msg, file=file, end=end)


def info(msg, file=None, end='\n', use_prefix=True):
    file = file if file is not None else sys.stdout
    global _quiet
    msg = str(msg)
    if use_prefix:
        msg = _log_prefix + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file, end=end)
    return msg


def warning(msg, file=None, end='\n', use_prefix=True):
    file = file if file is not None else sys.stdout
    global _quiet
    msg = str(msg)
    if use_prefix:
        msg = ansi('yellowf') + _log_prefix + msg \
            + ansi('reset')
    else:
        msg = ansi('yellowf') + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file, end=end)
    return msg


def error(msg, file=None, end='\n', use_prefix=True, exit=False):
    file = file if file is not None else sys.stderr
    global _quiet
    msg = str(msg)
    if use_prefix:
        msg = ansi('redf') + ansi('boldon') + _log_prefix + msg + ansi('reset')
    else:
        msg = ansi('redf') + ansi('boldon') + msg + ansi('reset')
    if exit:
        sys.exit(msg)
    if not _quiet:
        print(msg, file=file, end=end)
    return msg


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
